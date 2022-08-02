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
SCRIPT_NAME = "za_kouga"
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
    notice_data.buyer = 'CAPE AGENCY FOR SUSTAINABLE INTEGRATED DEVELOPMENT IN RURAL AREAS CASIDRA'
    notice_data.buyer_internal_id = '7702915'
    try:
        notice_data.published_date = page_main.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[2]/div['+str(tender_html_element)+']/div[2]/span').text
        notice_data.published_date = re.findall('\d+ \w+ \d{4}', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%d %B %Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[2]/div['+str(tender_html_element)+']/a').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.end_date = page_main.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[2]/div['+str(tender_html_element)+']/div[3]/span').text
        notice_data.end_date = re.findall('\d+ \w+ \d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%d %B %Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.reference = page_main.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[2]/div['+str(tender_html_element)+']/div[1]/span').text
    except:
        pass

    try:
        notice_data.notice_url = page_main.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[2]/div['+str(tender_html_element)+']/a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            resource_url = []
            resources = page_details.find_elements(By.CSS_SELECTOR, '.documents a')
            for each_resource in resources:
                resource_url = each_resource.get_attribute('href')
                notice_data.resource_url.append(resource_url)
        except:
            pass

        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div[1]/div[2]'))).get_attribute('outerHTML')
        except:
            pass

    except:
        notice_data.notice_url = url

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
page_details = fn.init_chrome_driver()
wait = WebDriverWait(page_main, 20)
wait_detail = WebDriverWait(page_details, 20)
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.kouga.gov.za/notice-board'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div[1]/div[2]/div[2]/div[1]/span'))).text
    rows = page_main.find_elements(By.CSS_SELECTOR, '.tenderlisting')
    length = len(rows)
    print(length)
    for tender_html_element in range(2,length+2):
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
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("africa")

