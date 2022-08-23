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
SCRIPT_NAME = "ca_sdcounty"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.performance_country = "Canada"
    notice_data.contact_country = "Canada"
    notice_data.buyer = "County of San Diego"
    notice_data.buyer_internal_id = "7787380"

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) a').get_attribute('href')
    except:
        return

    try:
        notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(4) span').text
        notice_data.published_date = re.findall('\d+/\d+/\d{4}', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%m/%d/%Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(5) span').text
        notice_data.end_date = re.findall('\d+/\d+/\d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%m/%d/%Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3) span').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2) span').text.strip()
    except:
        pass

    try:
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[3]/table'))).get_attribute('outerHTML')
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
wait = WebDriverWait(page_main, 20)
wait_detail = WebDriverWait(page_details, 20)
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://buynet.sdcounty.ca.gov/Solicitations/OpenSolicitations.aspx?SortTable=RFQ&SortField=LastChangeDate&SortOrder=Descend&RegUser=Guest'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[3]/table[2]/tbody/tr[2]/td[3]/span'))).text
    for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[3]/table[2]/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[1:]:
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
    output_xml_file.copyFinalXMLToServer("latin")

