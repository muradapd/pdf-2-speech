"""
You will need to install the AWS cli and configure it yourself.
"""

# TODO:
# - Finish documentation
# - Would be cool if the code could automatically add the mp3 files to iTunes 


PDF_FILES_ROOT = "pdf_files/"
MP3_FILES_ROOT = "mp3_files/"
PDF_FILE_NAME = "networking_textbook.pdf" # <- change this to change the file to synthesize DO NOT INCLUDE .pdf
BUCKET_NAME = "muradaz-mp3-files"
# NOTE: The page range must be negatively offset by 1 page to work.
CHAPTER_RANGES = [ # Update this array to synthesize the chapters
    {"name": "chapter_1", "range": range(28, 93)},
    {"name": "chapter_2", "range": range(108, 192)}
]

# Start the PDF-2-Speech process by running: "python runner.py"