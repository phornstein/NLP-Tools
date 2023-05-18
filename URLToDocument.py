'''
Title: URLToDocument
Author: Tim Murphy (tmurphy@esri.com), Parker Hornstein (phornstein@esri.com)
Date: May, 2023
Version: 1.0
Requires: Python 3.7+
Restrictions: None

Utility script to download page contents for a CSV of URLs and save
to a folder to prepare for NLP processing

Copyright © 2023 Esri
All rights reserved under the copyright laws of the United States and applicable international 
laws, treaties, and conventions. You may freely redistribute and use this sample code, with or 
without modification, provided you include the original copyright notice and use restrictions.

Disclaimer: THE SAMPLE CODE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
INCLUDING THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL ESRI OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) SUSTAINED BY 
YOU OR A THIRD PARTY, HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT 
LIABILITY, OR TORT ARISING IN ANY WAY OUT OF THE USE OF THIS SAMPLE CODE, EVEN IF ADVISED OF THE 
POSSIBILITY OF SUCH DAMAGE.

Esri
Attn: Contracts and Legal Services Department
380 New York Street
Redlands, California, 92373-8100 USA
email: contracts@esri.com
'''

import argparse
import os
import PyPDF2
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime as dt

def getTextfromHTML(html):
    '''
    Strip HTML from HTML documents and return just the text.
    Dev: Tim Murphy
    '''
    soup = BeautifulSoup(html, "html.parser")

	# kill all script and style elements
    for script in soup(["script", "style"]):
        script.decompose()    # rip it out

	# get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def pdfToText(fileLocation):
	'''
    Given the location of a PDF, get the text and return it.
    Dev: Tim Murphy
    '''

	# creating a pdf file object 
	pdfFileObj = open(fileLocation, 'rb') 

	try:
		pdfReader = PyPDF2.PdfFileReader(pdfFileObj) 		
		print("Number of pages: " + str(pdfReader.numPages))
		counter = 0
		text = ""
		upperLimit = pdfReader.numPages

		while (counter < upperLimit):
			pageObj = pdfReader.getPage(counter) 
				
			try:
				if (text != ""):
					text = text + "\n" + pageObj.extractText()
				else:
					text = pageObj.extractText()
			except Exception as e:
				print("Text not found in document.", e)
			counter += 1			
		pdfFileObj.close() 

	except Exception as e: 
		print("PDF Text Extract Failed - error.", e)
		return ""

	#Clean up the text
	text = text.replace(","," ")
	text = ' '.join(text.splitlines())
	WHITE_SPACE_PATTERN = re.compile(r' +')
	text = re.sub(WHITE_SPACE_PATTERN, ' ', text.strip())
	
def getTextFromFile(FileWithPath,ext):
    '''
    getTextFromFile : This handles the right way to get text out of a PDF or html or other
    Dev: Tim Murphy
    '''
    if ext == '.pdf':
        text = pdfToText(FileWithPath)
    else:
        with open(FileWithPath, "rb") as infile:
            text = getTextfromHTML(infile.read())
    return text

def getUrl(url,fileOut):
    '''
    Given a URL, save the result to a file and/or back to whatever called it
    PDF can be saved directly to a file
    Dev: Tim Murphy
    '''
    try:
        headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'}
        response = requests.get(url=url,headers=headers)
        with open(fileOut,'wb+') as outfile:
            outfile.write(response.content)
        return True
    except Exception as e:
        print(">>>Exception in getting the URL:" + str(e))
        return False
    
def processURL(url,outputDir):
    '''
    Requests an input URL, constructs a filename, and write file to content

    Return:
    -------
    dict : python dictionary with keys name, ext, url, text
    '''
    url = url.strip()
    file_name = Path(url).stem
    file_ext = Path(url).suffix

    #assume content is html if not otherwise specified
    if not file_ext == ".pdf":
        file_ext = ".html"

    #replace web chars with file chars
    file_name = file_name.replace("?","_")

    file_path = os.path.join(outputDir,f'{file_name}{file_ext}')
    result = getUrl(url,file_path)
    if not result:
          print(f"ERROR Processing: {file_name}")
          return None
    return {'name':file_name,
            'ext':file_ext,
            'url':url,
            'text':getTextFromFile(file_path,file_ext)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o","--output-directory",required=True,help="Output directory for saved files. Will be created if does not exist.")
    parser.add_argument("-i","--input-csv",required=True,help="Path to CSV containing URLs to download")
    parser.add_argument("-u","--url-field",required=True,help="Field in CSV containing URL string.")

    args = parser.parse_args()
    OUTPUT_DIR = args.output_directory
    INPUT_CSV = args.input_csv
    URL_COLUMN = args.url_field

    if not os.path.isdir(OUTPUT_DIR):
         os.mkdir(OUTPUT_DIR)

    #output directory for saved files
    files_dr = os.path.join(OUTPUT_DIR,'files')
    if not os.path.isdir(files_dr):
        os.mkdir(files_dr)
    print(f"{dt.now()} | Output File Directory: {files_dr}")

    #csv with files content
    content_csv = os.path.join(OUTPUT_DIR,'content.csv')
    print(f"{dt.now()} | Output Content CSV: {content_csv}")
    content = []

    #read csv and check fields
    urls_df = pd.read_csv(INPUT_CSV)
    url_count = len(urls_df.index) + 1
    if not URL_COLUMN in list(urls_df.columns):
         print(f"{dt.now()} | FIELD: {URL_COLUMN} NOT FOUND IN CSV FIELDS: {list(urls_df.columns)}")
         print(f"EXITING...")
         exit(0)

    #process URLs
    print(f"{dt.now()} | Found {url_count} URLs")
    for ind,row in urls_df.iterrows():
        progress = f"{ind+1}/{url_count}".ljust(10)
        print(f"{dt.now()} | Processing {progress} | {row[URL_COLUMN]}")
        try:
            result = processURL(row[URL_COLUMN],files_dr)
            if result:
                content.append(result)
        except Exception as e:
            print(f"ERROR: {row[URL_COLUMN]} \n {str(e)}")
    
    content_df = pd.DataFrame.from_dict(content)
    content_df.to_csv(content_csv)

if __name__=="__main__":
    main()