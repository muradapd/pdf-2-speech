# This code takes a PDF file, your other specified parameters (variables below), and 
# your AWS CLI (details below) as input. It then splits the PDF file into chapters 
# (using your specified parameters) and converts those chapters into MP3 files of 
# human like speech. The code uses AWS Polly and S3 to handle the actual text-to-speech 
# synthesis. AWS Polly tasks are started progrmatically and their output is sent to S3. 
# These output MP3 files are then downloaded from S3 and concatenated into single 
# chapter MP3 files. To learn about AWS pricing, you can visit the pricing calculator
# here: https://calculator.aws/#/addService

# You will need to install the AWS cli and configure it yourself. Basic instructions
# can be found below. For more detailed information, you can go to:
# https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html
 
# The AWS CLI (Command Line Interface) allows you to manage your AWS services from 
# the command line. To install and configure the AWS CLI, you can follow these steps:
#   1.  Make sure you have Python 2 version 2.6.5+ or Python 3 version 3.3+ installed 
#       on your computer. You can check your version by running: "python --version".
#   2.  Install the AWS CLI using pip, the Python package manager. 
#       To do this, run: "pip install awscli".
#   3.  Once the AWS CLI is installed, you can verify by running: "aws --version".
#       This should print the version number of the AWS CLI that you have installed.
#   4.  After validating the install, configure the CLI by running: "aws configure". 
#       You will be prompted for your AWS Access Key, Secret Key, Region, and the
#       default output you prefer. You can generate these keys using the IAM console.
# Please note that these instructions are for installing the AWS CLI on a computer 
# running Linux, macOS, or Windows. The installation process may be different on 
# other operating systems.

# Once the AWS CLI is installed and configured, you will need to create an S3 bucket.
# This bucket will be used to accept the AWS Polly task output MP3 files. To create a 
# new S3 bucket using the AWS CLI (in the region specified during CLI # configuration), 
# you can use the aws s3 mb (make bucket) command. A simple example of how to use this 
# command to create a new S3 bucket is: "aws s3 mb s3://my-new-bucket"

# Once you have the AWS CLI set up, and the S3 bucket created, you will need to edit 
# these parameters for the system to work for your needs. The runner.py file uses 
# these params to inform all of its processes.
PDF_FILES_ROOT = "pdf_files/" # <- change this to use a different PDF files source folder
MP3_FILES_ROOT = "mp3_files/" # <- change this to use a different MP3 files destination folder
PDF_FILE_NAME = "networking_textbook.pdf" # <- change this to the file you want to synthesize
BUCKET_NAME = "muradaz-mp3-files" # <- change this to the S3 bucket you made for Polly output
CHAPTER_RANGES = [ # <- update this to include all chapter page ranges to synthesize 
    {"name": "chapter_1", "range": range(28, 93)},
    {"name": "chapter_2", "range": range(108, 192)}
]
# NOTE: The page ranges must be negatively offset by 1 page to work. For example, 
# if the chapter starts on page 30 and ends on page 40, the range would be (29, 39).

# Now that you have set everything up, you are ready to run the program!
# To start the PDF-2-Speech process, simply run the command: "python runner.py"