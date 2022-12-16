"""
 * NOTE: This runner file should not need to be edited to meet your needs.
 * See the instructions in the user.py file before making changes to this file.
"""
import PyPDF2, boto3, threading, os, sys
import time, user, shutil, subprocess
from pydub import AudioSegment

# Global variables used throughout the script
POLLY_CLIENT = boto3.client("polly")
S3_CLIENT = boto3.client("s3")
BUCKET_NAME = user.BUCKET_NAME
PDF_FILES_ROOT = user.PDF_FILES_ROOT
MP3_FILES_ROOT = user.MP3_FILES_ROOT
PDF_FILE_NAME = user.PDF_FILE_NAME
CHAPTER_RANGES = user.CHAPTER_RANGES
CHAPTER_MP3_FILES = []

# Puts the current chapter's concatenated MP3 file in S3. Then cleans up all 
# of the working directories by deleting the no longer needed task output MP3s.
def cleanup_chapter(chapter_name):
    print("Cleaning up the chapter working dirs...")
    os_working_dir = MP3_FILES_ROOT + PDF_FILE_NAME.replace(".pdf", "") + \
        "/" + chapter_name
    s3_working_dir = "%s/%s/" % (PDF_FILE_NAME.replace(".pdf", ""), chapter_name)
    body_file = os_working_dir + ".mp3"
    mp3_key = PDF_FILE_NAME.replace(".pdf", "") + "/" + chapter_name + ".mp3"
    shutil.rmtree(os_working_dir)
    with open(body_file, 'rb') as f:
        S3_CLIENT.put_object(Body=f, Bucket=BUCKET_NAME, Key=mp3_key)
    res = S3_CLIENT.list_objects_v2(Bucket=BUCKET_NAME, Prefix=s3_working_dir)
    objects = [{'Key': obj['Key']} for obj in res['Contents'] if obj['Key'].startswith(s3_working_dir)]
    S3_CLIENT.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': objects})

# Concatenates all of the Polly task MP3 files from S3 into a single MP3 file 
# for the current chapter. Saves this single MP3 file to the local machine.
def concatenate_mp3_files(chapter_name):
    global CHAPTER_MP3_FILES
    print("Concatenating %s mp3 files..." % chapter_name)
    initial_file = CHAPTER_MP3_FILES[0]
    other_files = CHAPTER_MP3_FILES[1:]
    concatenated_file = AudioSegment.from_mp3(initial_file)
    for file in other_files:
        file_sound = AudioSegment.from_mp3(file)
        concatenated_file += file_sound
    file_path = MP3_FILES_ROOT + PDF_FILE_NAME.replace(".pdf", "") + "/"
    concatenated_file.export(file_path + chapter_name + ".mp3", format="mp3")
    CHAPTER_MP3_FILES = []

# Downloads the given Poly task's MP3 file from S3 to the local machine.
def download_from_s3(task, prefix):
    key = "%s.%s.mp3" % (prefix, task["id"])
    print("Task DONE! Downloading %s mp3 file from S3..." % key)
    S3_CLIENT.download_file(BUCKET_NAME, key, MP3_FILES_ROOT + key)
    print("File downloaded to: %s" % key)

# Asynchronously monitors the given Poly task on a newly created thread.
def monitor_task(first_run, task, prefix):
    res = POLLY_CLIENT.get_speech_synthesis_task(TaskId=task["id"])
    task_status = res["SynthesisTask"]["TaskStatus"]
    if task_status == "completed": download_from_s3(task, prefix)
    elif task_status == "failed": 
        print("Failure reason: %s" % res["SynthesisTask"]["TaskStatusReason"])
    else:
        if not first_run:
            format = (task["id"], task_status)
            print("Task %s status: %s. Waiting 10 seconds." % format)
        time.sleep(10)
        monitor_task(False, task, prefix)
        
# Converts the given chapter text to speech using AWS Polly. To get
# around the Poly text limit, we split the chapter into strings of
# 15,000 chars each. We then start a Poly task for each new string.
def text_to_speech(text, prefix):
    if len(text) == 0: print("Skipping chapter since length is 0."); return
    sub_texts = [text[i:i+15000] for i in range(0, len(text), 15000)]
    stl = len(sub_texts); p = 0
    for sub_text in sub_texts:
        p += 1; print("(%s/%s) Synthesis task kicking off..." % (p, stl))
        res = POLLY_CLIENT.start_speech_synthesis_task(
            Engine="standard",
            OutputFormat="mp3",
            OutputS3BucketName=BUCKET_NAME,
            OutputS3KeyPrefix=prefix,
            Text=sub_text,
            VoiceId="Joanna"
        )
        task = {
            "id": res["SynthesisTask"]["TaskId"],
            "status": res["SynthesisTask"]["TaskStatus"],
            "out_uri": res["SynthesisTask"]["OutputUri"],
            "created_at": res["SynthesisTask"]["CreationTime"],
            "req_chars": res["SynthesisTask"]["RequestCharacters"]
        }
        print("Task ID: %s - Status: %s" % (task["id"], task["status"]))
        if task["status"] == "failed":
            reason = res["SynthesisTask"]["TaskStatusReason"]
            print("Failure reason: %s" % reason)
            print("---------------------------------------------")
        else: 
            CHAPTER_MP3_FILES.append("%s%s.%s.mp3" % (MP3_FILES_ROOT, prefix, task["id"]))
            print("Monitoring task: %s..." % task["id"])
            print("---------------------------------------------")
            threading.Thread(target=monitor_task, args=(True, task, prefix)).start()

# Extracts the text from the PDF file for the given chapter page range.
def get_chapter_text(pdf, chapter_range):
    print("Parsing text for %s..." % (chapter_range["name"]))
    chapter_text = ""; chrng = chapter_range["range"]
    pages_length = chrng.stop - chrng.start
    
    for page_num in chrng:
        text = pdf.getPage(page_num).extractText()
        if page_num % 10 == 0: 
            format = (page_num - chrng.start, pages_length)
            print("%s/%s pages read." % format)
        if len(text) > 0: chapter_text = chapter_text + text
    print("Text parsed successfully.")
    return chapter_text

# Creates an S3 folder, in your specified bucket, for the given chapter.
def create_chapter_s3(folder_name):
    print("Creating %s folder in S3..." % folder_name)
    try:
        S3_CLIENT.head_object(Bucket=BUCKET_NAME, Key=folder_name)
        print("Folder already exists in S3. Moving on.")
    except Exception as e:
        if e.response["Error"]["Code"] == "404":
            S3_CLIENT.put_object(Bucket=BUCKET_NAME, Key=folder_name)
            print("Folder created successfully.")
        else: raise

# Synthesizes all of the chapters that were specified by the user
# in the user.py file. This is more of an orchestration function
# as it loops through each user-defined chapter and uses the above
# helper functions to actually synthesize each chapter into speech.
def synthesize_chapters():
    print("Opening & reading PDF file: %s" % PDF_FILE_NAME)
    with open(PDF_FILES_ROOT + PDF_FILE_NAME, "rb") as file:
        pdf = PyPDF2.PdfFileReader(file)
        print("PDF file Opened and read.")
        for chapter_range in CHAPTER_RANGES:
            chapter_name = chapter_range["name"]
            s3_pdf_dir = PDF_FILE_NAME.replace('.pdf', '')
            prefix = "%s/%s/" % (s3_pdf_dir, chapter_name)
            os_mp3_dir = MP3_FILES_ROOT + prefix
            if not os.path.exists(os_mp3_dir): os.makedirs(os_mp3_dir)
            print("---------------------------------------------")
            create_chapter_s3(prefix)
            print("---------------------------------------------")
            text = get_chapter_text(pdf, chapter_range)
            print("---------------------------------------------")
            text_to_speech(text, prefix)
            while threading.active_count() > 1: time.sleep(10)
            print("---------------------------------------------")
            concatenate_mp3_files(chapter_name)
            cleanup_chapter(chapter_name)
            print("%s is fully COMPLETE!\n\n" % chapter_name)
    print("All chapters fully COMPLETE! Thanks for using PDF-2-Speech!")

# Installs all of the necessary python packages using pip
def install_packages():
    packages = ['pyffmpeg', 'PyPDF2', 'boto3', 'pydub']
    print("---------------------------------------------")
    print("Installing necessary packages: ", packages)
    print("---------------------------------------------")
    for package in packages:
        print("Installing:", package, "...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(package, "installed!")
        print("---------------------------------------------")

if __name__ == "__main__":
    install_packages()
    synthesize_chapters()