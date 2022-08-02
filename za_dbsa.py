import logging
import re
import time
from datetime import date, datetime, timedelta
from deep_translator import GoogleTranslator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 2000
SCRIPT_NAME = "za_dbsa"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'South Africa'
    notice_data.contact_country = 'South Africa'
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.buyer = 'Development Bank of Southern Africa (DBSA)'
    notice_data.buyer_internal_id = '7139990'

    try:
        notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)').text
        notice_data.published_date = re.findall('\d{4}/\d+/\d+', notice_data.published_date)[0]
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) a').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text
        notice_data.end_date = re.findall('\d{4}/\d+/\d+', notice_data.end_date)[0]
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) strong').text
        notice_data.reference = notice_data.reference.replace(':','').strip()
    except:
        pass

    try:
        extension_pdf_url = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) a').get_attribute('href')
        notice_data.notice_url = extension_pdf_url
    except:
        pass

    try: 
        if notice_data.cpvs == [] and notice_data.title_en is not None:
            notice_data.cpvs = fn.assign_cpvs_from_title(notice_data.title_en.lower(),notice_data.category)
    except:
        pass

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
    url = 'https://www.dbsa.org/procurement'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[3]/main/section/div/div[2]/article/div/div/div/div/div/table[1]/tbody/tr[1]/td[1]/a'))).text
    for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/main/section/div/div[2]/article/div/div/div/div/div/table[1]/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
        extract_and_save_notice(tender_html_element)
        if notice_count >= MAX_NOTICES:
            break

        if notice_data.published_date is not None and  notice_data.published_date < threshold:
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
    output_xml_file.copyFinalXMLToServer("africa")

