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
SCRIPT_NAME = "za_joburg"
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
    notice_data.buyer = 'CITY OF JOHANNESBURG'
    notice_data.buyer_internal_id = '7133212'

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text
        notice_data.end_date = re.findall('\d+ \w+ \d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%d %B %Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.end_date is not None and notice_data.end_date < threshold:
        return

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) a').text
    except:
        pass

    try:
        notice_data.resource_url = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) a').get_attribute('href')
    except:
        pass

    notice_data.notice_url = notice_data.resource_url

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
    urls = ['https://www.joburg.org.za/work_/Pages/Work%20in%20Joburg/Tenders%20and%20Quotations/2022%20Tenders%20and%20Quotations/2022%20TENDERS/BID%20OPENING%20REGISTERS/Invitation%20to%20Bid.aspx',
            'https://www.joburg.org.za/work_/Pages/Work%20in%20Joburg/Tenders%20and%20Quotations/2022%20Tenders%20and%20Quotations/2022%20RFQ%27s/June/Current-RFQs.aspx']
    logging.info('----------------------------------')
    for url in urls:
        fn.load_page(page_main, url)
        logging.info(url)

        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[5]/div/div/div[2]/div/div/div[2]/span/div[1]/div[2]/div[2]/table/tbody/tr[2]/td[2]'))).text
        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[5]/div/div/div[2]/div/div/div[2]/span/div[1]/div[2]/div[2]/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[1:]:
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.end_date is not None and  notice_data.end_date < threshold:
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

