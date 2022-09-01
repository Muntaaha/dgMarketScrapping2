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
SCRIPT_NAME = "uk_contractsfinder"

notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data  
    notice_data = NoticeData()

    notice_data.performance_country = 'United Kingdom'
    notice_data.contact_country = 'United Kingdom'
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'

    try:
        try:
            published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'div:nth-child(11)').text.strip()
        except:
            published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'div:nth-child(10)').text.strip()
        published_date = re.findall('\d+ \w+ \d{4}',published_date)[0]
        notice_data.published_date = datetime.strptime(published_date,'%d %B %Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.buyer = tender_html_element.find_element(By.CSS_SELECTOR, '.search-result-sub-header.wrap-text').text
    except:
        pass

    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR, '.search-result-header h2 a').text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
    except:
        pass

    try:
        end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'div:nth-child(8)').text.strip()
        end_date = re.findall('\d+ \w+ \d{4}',end_date)[0]
        notice_data.end_date = datetime.strptime(end_date,'%d %B %Y').strftime('%Y/%m/%d')
    except:
        pass
        
    
    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, '.search-result-header h2 a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += WebDriverWait(page_details, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR,'#standard-body #all-content-wrapper'))).get_attribute('outerHTML')
        except:
            pass
    except:
        notice_data.notice_url = url

    notice_data.cleanup()
   
    logging.info('---------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body

page_main = fn.init_chrome_driver()
page_details = fn.init_chrome_driver()

try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.contractsfinder.service.gov.uk/Search/Results?page=1#25dcc4b8-3942-40af-a394-0612e615f766'
    fn.load_page(page_main, url)
    logging.info(url)
    
    for page_num in range(2,5):                                                                   
        page_check = WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[3]/div[2]/div/div/div/div/div[3]/div/div/div/div[1]/div[1]/div[1]/h2/a'))).text
        for tender_html_element in  WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.gadget.partial-gadget'))).find_elements(By.CSS_SELECTOR, '.search-result'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

        if notice_data.published_date is not None and  notice_data.published_date < threshold:
            break
      
        try:
            next_page = 'https://www.contractsfinder.service.gov.uk/Search/Results?&page='+str(page_num)+'#dashboard_notices'
            fn.load_page(page_main, next_page)
            logging.info("Next page")
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[3]/div[2]/div/div/div/div/div[3]/div/div/div/div[1]/div[1]/div[1]/h2/a'),page_check))
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
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("europe")

