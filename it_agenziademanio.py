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
SCRIPT_NAME = "it_agenziademanio"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "IT"
    notice_data.notice_type = 'spn'
    notice_data.performance_country = "Italy"
    notice_data.contact_country = "Italy"

    try:
        notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, '.datapubblicazione').text
        notice_data.published_date = re.findall('\d+ \w+ \d{4}', notice_data.published_date)[0]
        notice_data.published_date = dateparser.parse(notice_data.published_date, settings={'DATE_ORDER': 'DMY'})
        notice_data.published_date = str(notice_data.published_date)
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%Y-%m-%d %X').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return
    
    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, '.CIG').text
        notice_data.reference = notice_data.reference.split('CIG:')[1].strip()
    except:
        pass
    
    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, '.datascadenza').text
        notice_data.end_date = re.findall('\d+ \w+ \d{4}', notice_data.end_date)[0]
        notice_data.end_date = dateparser.parse(notice_data.end_date, settings={'DATE_ORDER': 'DMY'})
        notice_data.end_date = str(notice_data.end_date)
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%Y-%m-%d %X').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, '.title a').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.buyer = tender_html_element.find_element(By.CSS_SELECTOR, '.comune span:nth-of-type(2)').text.strip()
        if notice_data.buyer == '':
            return
    except:
        return

    try:
        notice_data.notice_url = page_main.find_element(By.CSS_SELECTOR, '.title a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += WebDriverWait(page_details, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR,'#main'))).get_attribute('outerHTML')
        except:
            pass

        try:
            notice_data.resource_url = []
            resources = page_details.find_element(By.CSS_SELECTOR,'.documentigara').find_elements(By.CSS_SELECTOR, '.documento')
            for each_resource in resources:
                resource_url = each_resource.find_element(By.CSS_SELECTOR,'a').get_attribute('href')
                notice_data.resource_url.append(resource_url)
        except:
            pass

    except:
        notice_data.notice_url = url

    notice_data.cleanup()
    logging.info('-------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body
page_main = fn.init_chrome_driver()
page_details = fn.init_chrome_driver()
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.agenziademanio.it/opencms/it/gare-aste/forniture-e-servizi/'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[4]/div/div/div[1]/main/div[2]/div[1]/div/div/div[2]/div[1]/div/div/div/h2/a'))).text

    for tender_html_element in WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.solr-list'))).find_elements(By.CSS_SELECTOR, '.cols'):
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
    output_xml_file.copyFinalXMLToServer("europe")

