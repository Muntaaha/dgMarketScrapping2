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
SCRIPT_NAME = "th_pwa"

notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data  
    notice_data = NoticeData()

    notice_data.performance_country = 'Thailand'
    notice_data.contact_country = 'Thailand'
    notice_data.procurement_method = "Other"
    notice_data.language = "TH"
    notice_data.notice_type = 'spn'
    notice_data.buyer  = 'PROVINCIAL WATERWORKS AUTHORITY'
    notice_data.buyer_internal_id = '7696951'

    try:
        published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(5)').text.strip()
        published_date = GoogleTranslator(source='auto', target='en').translate(published_date)
        published_date = published_date.replace('.','').strip()
        published_date = re.findall('\d+ \w+ \d{4}',published_date)[0]
        notice_data.published_date = datetime.strptime(published_date,'%d %b %Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        return

    if notice_data.published_date is not None and notice_data.published_date.split('/')[0] != threshold.split('/')[0]:
        return

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(2) a').text
    except:
        pass

    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(3) a').text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
    except:
        pass
        
    
    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-child(2) a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += WebDriverWait(page_details, 180).until(EC.presence_of_element_located((By.CSS_SELECTOR,'.page-header'))).get_attribute('outerHTML')
            notice_data.notice_text += WebDriverWait(page_details, 180).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div[2]'))).get_attribute('outerHTML')
        except:
            pass

        try:
            notice_data.resource_url = []
            resources = page_details.find_element(By.CSS_SELECTOR,'ul').find_elements(By.CSS_SELECTOR, 'li')
            for each_resource in resources:
                resource_url = each_resource.find_element(By.CSS_SELECTOR,'a').get_attribute('href')
                notice_data.resource_url.append(resource_url)
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
    url = 'https://eprocurement.pwa.co.th/e-bidding/page/1'
    fn.load_page(page_main, url)
    logging.info(url)
    
    for page_num in range(2,7):                                                                   
        page_check = WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div/table/tbody/tr[1]/td[2]/a'))).text
        for tender_html_element in  WebDriverWait(page_main, 180).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

        if notice_data.published_date is not None and  notice_data.published_date < threshold:
            break
      
        try:
            next_page = 'https://eprocurement.pwa.co.th/e-bidding/page/'+str(page_num)
            fn.load_page(page_main, next_page)
            logging.info("Next page")
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div/table/tbody/tr[1]/td[2]/a'),page_check))
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
    output_xml_file.copyFinalXMLToServer("asia")