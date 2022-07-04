import logging
import re
import time
from datetime import date, datetime, timedelta
# from deep_translator import GoogleTranslator
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 20000

notice_count = 0
output_xml_file = common.OutputXML.OutputXML("my_selangor")

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    wait_detail = WebDriverWait(page_details, 20)
    
    notice_data.cpvs.clear()
    notice_data.performance_country = 'Malaysia'
    notice_data.contact_country = 'Malaysia'
    notice_data.procurement_method = "Other"
    notice_data.language = "MS"
    notice_data.notice_type = 'spn'
    notice_data.buyer_internal_id = 'N/A'


    notice_data.buyer = 'ORLEN SA'
    
    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(1) a").text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
    except:
        pass
    
    try:
        notice_data.referance = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(1) small strong u").text
    except:
        pass

    try:
        published_date = page_details.find_element(By.XPATH, "td:nth-of-type(3)").text
        published_date = re.findall('\d+ \w+ \d{4}',published_date)[0]
        notice_data.published_date =  datetime.strptime(published_date, '%d %b %Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and  notice_data.published_date < threshold:
        return

    try:
        end_date = page_details.find_element(By.XPATH, "td:nth-of-type(4)").text
        end_date = re.findall('\d+ \w+ \d{4}',end_date)[0]
        notice_data.end_date =  datetime.strptime(end_date, '%d %b %Y').strftime('%Y/%m/%d')
    except:
        pass
    
    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(1) a").get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)
        
        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div/div/div[5]/div[2]/div[2]/table/tbody'))).text
        except:
            pass
        
        try:
            notice_data.buyer = page_details.find_element(By.XPATH, "/html/body/div[2]/div/div/div[5]/div[2]/div[2]/table/tbody/tr[1]/td").text
        except:
            pass
        
        
    except:
        notice_data.notice_url = url
    
    if notice_data.cpvs == [] and notice_data.title_en is not None:
        notice_data.cpvs = fn.assign_cpvs_from_title(notice_data.title_en.lower(),notice_data.category)
        
    notice_data.cleanup()
    logging.info('-------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1
    
# ----------------------------------------- Main Body

page_main = fn.init_chrome_driver()
page_details = fn.init_chrome_driver()
wait = WebDriverWait(page_main, 20)

th = date.today() - timedelta(1)
threshold = th.strftime('%Y/%m/%d')
logging.info("Scraping from or greater than: " + threshold)

try:
    url = 'https://tender.selangor.my/'
    logging.info(url)
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    
    for page in range(25):

        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div/div[3]/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            try:
                more_notices = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div/div[3]/div[2]/div/div[2]/div/ul/li[7]/a'))).click()
                logging.info('click')
            except:
                page_main.refresh()
                more_notices = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div/div[3]/div[2]/div/div[2]/div/ul/li[7]/a'))).click()
                logging.info('click')
        except:
            break
             

    
    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log('my_selangor', notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log('my_selangor', e)
        fn.session_log('my_selangor', notice_count, 'Script error')
    except:
        pass
    raise e
finally:
    page_main.quit()
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("europe")