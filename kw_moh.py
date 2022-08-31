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
SCRIPT_NAME = "ku_moh"

notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data  
    notice_data = NoticeData()

    notice_data.performance_country = 'Kuwait'
    notice_data.contact_country = 'Kuwait'
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.buyer  = 'MINISTRY OF HEALTH'
    notice_data.buyer_internal_id = '7524824'
    notice_data.notice_url = url
    
    try:
        published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(5)').text
        notice_data.published_date = datetime.strptime(published_date,'%d/%m/%Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return
    
    try:
        end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(6)').text
        notice_data.end_date = re.findall('\d+/\d+/\d{4}',end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date,'%d/%m/%Y').strftime('%Y/%m/%d')
        logging.info(notice_data.end_date)
    except:
        pass
    
    try:
        organization_name = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(4)').text
        notice_data.organization_name = GoogleTranslator(source='auto', target='en').translate(organization_name)
        logging.info(notice_data.organization_name)
    except:
        pass
    
    try:
        reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(2)').text
        notice_data.reference =  GoogleTranslator(source='auto', target='en').translate(reference)
        logging.info(notice_data.reference)
    except:
        pass
    
    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(3)').text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
        logging.info(notice_data.title_en)
    except:
        pass
    
    try:
        notice_data.notice_text += tender_html_element.get_attribute('outerHTML')
    except:
        pass

    notice_data.cleanup()
   
    logging.info('---------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body

# this code is for vpn purpose--------------------------------
page_main = fn.init_chrome_driver()
options = webdriver.ChromeOptions()
options.add_extension("Hola-VPN---The-Website-Unblocker.crx")
page_main = webdriver.Chrome(options=options)
time.sleep(80)

try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://eservices.moh.gov.kw/pdApps/CompanyRegistration/v1/ViewTenders'
    fn.load_page(page_main, url,80)
    logging.info(url)
    
    for page_num in range(2,6):                                                                   
        page_check = WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH,'//*[@id="gv1"]/tbody/tr[2]'))).text
        for tender_html_element in  WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH, '//*[@id="gv1"]/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[1:-2]:
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

        if notice_data.published_date is not None and notice_data.published_date < threshold:
            break
      
        try:
            next_page = WebDriverWait(page_main, 50).until(EC.element_to_be_clickable((By.LINK_TEXT,str(page_num) )))
            page_main.execute_script("arguments[0].click();",next_page)
            logging.info("Next page")
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'//*[@id="gv1"]/tbody/tr[2]'),page_check))
        except:
            logging.info("No Next Page")
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
    output_xml_file.copyFinalXMLToServer("asia")