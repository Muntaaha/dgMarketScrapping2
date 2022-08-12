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
SCRIPT_NAME = "jp_shutoko"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "JP"
    notice_data.notice_type = 'spn'
    notice_data.performance_country = "Japan"
    notice_data.contact_country = "Japan"

    try:
        notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, '.is-t2 .tdinner').text
        notice_data.published_date = re.findall('\d{4}.\d+.\d+', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%Y.%m.%d').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, '.is-t6 .tdinner').text
        notice_data.end_date = re.findall('\d{4}.\d+.\d+', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%Y.%m.%d').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, '.is-t5 .tdinner').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.buyer = tender_html_element.find_element(By.CSS_SELECTOR, '.is-t3 .tdinner').text.strip()
    except:
        pass

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, '.is-t1 .tdinner .c-document__list__item.pdf a').get_attribute('href')

    except:
        notice_data.notice_url = url

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
    url = 'https://www.shutoko.co.jp/business/bid/'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div[2]/div[3]/div/div[1]/table[2]/tbody/tr/td[1]/div/div/a'))).text
    rows = page_main.find_elements(By.CSS_SELECTOR, '.js-bidtbinner')
    length = len(rows)
    for tender_html_element in wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.c-general__content'))).find_elements(By.CSS_SELECTOR, '.js-bidtbinner'):
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
    output_xml_file.copyFinalXMLToServer("asia")

