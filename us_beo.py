import logging
import time
from datetime import date, datetime, timedelta
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC   
from deep_translator import GoogleTranslator
from selenium import webdriver
from selenium.webdriver.common.by import By
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData
import re

MAX_NOTICES = 20000
SCRIPT_NAME = "us_beo"

notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data  
    notice_data = NoticeData()

    notice_data.procurement_method = "Other"
    notice_data.language = "ES"
    notice_data.notice_type = 'eoi'
    notice_data.buyer  = 'Inter-American Development Bank (IDB)'
    notice_data.buyer_internal_id = '493'

    try:
        published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(6)').text.strip()
        published_date = re.findall('\d+-\w+-\d{4}',published_date)[0]
        notice_data.published_date = datetime.strptime(published_date,'%d-%b-%Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        return

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(7)').text.strip()
        end_date = re.findall('\d+-\w+-\d{4}',end_date)[0]
        notice_data.end_date = datetime.strptime(end_date,'%d-%b-%Y').strftime('%Y/%m/%d')
        logging.info(notice_data.end_date)
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(1) a').text
    except:
        pass

    try:
        notice_data.performance_country = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(2)').text
        notice_data.contact_country = notice_data.performance_country
    except:
        pass

    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(5)').text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
    except:
        pass
    
    try:
        notice_data.notice_text += tender_html_element.get_attribute('outerHTML')
    except:
        pass
    
    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(1) a').get_attribute('href')
    except:
        notice_data.notice_url = url

    notice_data.cleanup()
   
    logging.info('---------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body

page_main = fn.init_chrome_driver()

try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://beo-procurement.iadb.org/home'
    fn.load_page(page_main, url)
    logging.info(url)
                                                                      
    page_check = WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div/div/div[6]/div/main/div/div/div[2]/div/div[2]/div[1]/div[2]/div[2]/div/div[2]/table/tbody/tr[1]/td[1]/a'))).text
    for tender_html_element in  WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[6]/div/main/div/div/div[2]/div/div[2]/div[1]/div[2]/div[2]/div/div[2]/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
        extract_and_save_notice(tender_html_element)
        if notice_count >= MAX_NOTICES:
            break

    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log(SCRIPT_NAME, notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log(SCRIPT_NAME, e)
        fn.session_log(SCRIPT_NAME, notice_count,'Script error')
    except:
        pass
    raise e
finally:
    page_main.quit()
    output_xml_file.copyFinalXMLToServer("north_america")