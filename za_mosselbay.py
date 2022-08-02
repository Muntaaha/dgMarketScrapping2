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
SCRIPT_NAME = "za_mosselbay"
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
    notice_data.buyer = 'Millennium Challenge Corporation (MCA)'
    notice_data.buyer_internal_id = '1308224'

    notice_data.reference = page_main.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1)').text.strip()
    if 'CANCELLATION OF TENDER:' in notice_data.reference:
        return

    try:
        notice_data.published_date = page_main.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text
        notice_data.published_date = re.findall('\d{4}-\d+-\d+', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%Y-%m-%d').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    # if notice_data.published_date is not None and notice_data.published_date < threshold:
    #     return

    try:
        notice_data.title_en = page_main.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.end_date = page_main.find_element(By.CSS_SELECTOR, 'td:nth-of-type(4)').text
        notice_data.end_date = re.findall('\d{4}-\d+ \d+', notice_data.end_date)[1]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%Y-%m-%d').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.notice_url = page_main.find_element(By.CSS_SELECTOR, 'td:nth-of-type(5) a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/section[3]/div[1]/div[2]/div/div[1]/div[2]'))).get_attribute('outerHTML')
        except:
            pass

        try:
            notice_data.resource_url =page_details.find_element(By.XPATH, '/html/body/div[2]/section[3]/div[1]/div[2]/div/div[1]/div[2]/a[1]').get_attribute('href')
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
    url = 'https://www.mosselbay.gov.za/procurement-index?tenders=display'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/section[4]/div/div[2]/div/div/div[1]/div/div/div/div/table/tbody/tr[1]/td[1]'))).text
    for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/section[4]/div/div[2]/div/div/div[1]/div/div/div/div/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
        extract_and_save_notice(tender_html_element)
        if notice_count >= MAX_NOTICES:
            break

        # if notice_data.published_date is not None and  notice_data.published_date < threshold:
        #     break
                
    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    # fn.session_log(SCRIPT_NAME, notice_count, 'XML uploaded')
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

