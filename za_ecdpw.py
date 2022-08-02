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
SCRIPT_NAME = "za_ecdpw"
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
    notice_data.buyer = 'EASTERN CAPE DEPARTMENT OF PUBLIC WORKS'
    notice_data.buyer_internal_id = '7680531'

    try:
        notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text
        notice_data.published_date = re.findall('\d{4}-\d+-\d+', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%Y-%m-%d').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2) .descriptionblock').text.strip()
        notice_data.title_en = notice_data.title_en.split('Region')[0].strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2) .descriptionblock').text
        notice_data.reference = notice_data.reference.split('Bid Number:')[1].strip()
    except:
        pass

    try:
        extension_pdf_url = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(4) a').get_attribute('href')
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
    url = 'https://www.ecdpw.gov.za/tenders/'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    for page_number in range(2,5):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div/main/div/div/div/article/div/div/div/div/div[2]/table/tbody/tr[1]/td[1]'))).text
        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/main/div/div/div/article/div/div/div/div/div[2]/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            url = 'https://www.ecdpw.gov.za/tenders/#'+str(page_number)
            fn.load_page(page_main, url)
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div/main/div/div/div/article/div/div/div/div/div[2]/table/tbody/tr[1]/td[1]'),page_check))
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
    output_xml_file.copyFinalXMLToServer("africa")

