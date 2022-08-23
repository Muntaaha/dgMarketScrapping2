import logging
import re
import time
from datetime import date, datetime, timedelta
import dateparser
from deep_translator import GoogleTranslator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 2000
SCRIPT_NAME = "ca_sasktenders"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    global row_number
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.performance_country = "Canada"
    notice_data.contact_country = "Canada"
    
    try:
        notice_data.published_date = page_main.find_element(By.XPATH, '/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div['+str(row_number)+']/table/tbody/tr/td[5]').text
        notice_data.published_date = re.findall('\w+ \d+, \d{4}', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%b %d, %Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.end_date = page_main.find_element(By.XPATH, '/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div['+str(row_number)+']/table/tbody/tr/td[6]').text
        notice_data.end_date = re.findall('\w+ \d+, \d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%b %d, %Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.reference = page_main.find_element(By.XPATH, '/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div['+str(row_number)+']/table/tbody/tr/td[4]').text
        notice_data.reference = notice_data.reference.split('\n')[1].strip()
    except:
        pass

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div['+str(row_number)+']/table/tbody/tr/td[2]').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.buyer = page_main.find_element(By.XPATH, '/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div['+str(row_number)+']/table/tbody/tr/td[3]').text.strip()
    except:
        pass
    row_number += 1
    try:
        notice_data.notice_text += wait.until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div['+str(row_number)+']/div/table/tbody/tr/td[2]/table/tbody'))).get_attribute('outerHTML')
    except:
        pass
    notice_data.notice_url = url

    row_number += 1

    notice_data.cleanup()
    logging.info('-------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body
page_main = fn.init_chrome_driver()
wait = WebDriverWait(page_main, 20)
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://sasktenders.ca/content/public/Search.aspx'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    for page_number in range(2):
        row_number = 1
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div[1]/table/tbody/tr/td[2]'))).text
        for tender_html_element in range(1,51):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:            
            page_main.find_element('/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[2]/table/tbody/tr[2]/td[3]/a').click()
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/form/div[8]/div/div/div[3]/div/div[3]/div/div/div/div[1]/div[2]/div[1]/table/tbody/tr/td[2]'),page_check))
            logging.info("Next Page")
        except:
            logging.info("No Next Page")
            break


    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log(SCRIPT_NAME, notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log(SCRIPT_NAME, e)
        fn.session_log(SCRIPT_NAME, notice_count, 'Script error')
    except:
        pass
    raise e
finally:
    logging.info('finally')
    page_main.quit()
    output_xml_file.copyFinalXMLToServer("latin")

