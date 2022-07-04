import logging
import re
import time
from datetime import date, datetime, timedelta
from deep_translator import GoogleTranslator
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
output_xml_file = common.OutputXML.OutputXML("cy_eprocurement")

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    wait_detail = WebDriverWait(page_details, 20)
    
    notice_data.cpvs.clear()
    notice_data.performance_country = 'Cyprus'
    notice_data.contact_country = 'Cyprus'
    notice_data.procurement_method = "Other"
    notice_data.language = "GR"
    
    notice_data.notice_type = "spn"  

    notice_data.buyer_internal_id = 'N/A'
    
    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(2) a").text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
    except:
        pass
    
    try:
        notice_data.buyer = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(3)").text
    except:
        pass
            
    try:
        published_date = page_details.find_element(By.CSS_SELECTOR, "td:nth-of-type(4)").text
        published_date = re.findall('\d+/\d+/\d{4}',published_date)[0]
        notice_data.published_date =  datetime.strptime(published_date, '%d/%m/%Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and  notice_data.published_date < threshold:
        return

    try:
        end_date = page_details.find_element(By.CSS_SELECTOR, "td:nth-of-type(5)").text
        end_date = re.findall('\d+/\d+/\d{4}',end_date)[0]
        notice_data.end_date =  datetime.strptime(end_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.est_cost = page_details.find_element(By.CSS_SELECTOR, "td:nth-of-type(12)").text
    except:
        pass

    notice_data.currency = 'CYP'
        

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(2) a").get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)
        
        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[5]/div[2]/dl'))).text
        except:
            pass
    
        try:
            notice_data.referance = tender_html_element.find_element(By.XPATH,"/html/body/div[1]/div[5]/div[2]/dl/dd[4]").text
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

    url = 'https://www.eprocurement.gov.cy/epps/quickSearchAction.do?latest=true&searchSelect=1&selectedItem=quickSearchAction.do%3Flatest%3Dtrue%26searchSelect%3D1'  
    logging.info(url)
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    
    submit = WebDriverWait(page_main, 30).until(EC.presence_of_element_located((By.XPATH,'//*[@id="cookieModalConsent"]')))
    page_main.execute_script("arguments[0].click();",submit)

    for page in range(26):
             
        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[5]/div[2]/form/div/div/div[1]/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break


        try:
            more_notices = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[5]/div[2]/form/div/div/div[2]/p[2]/button[3]'))).click()
            logging.info('click')
        except:
            break
    
    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log('cy_eprocurement', notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log('cy_eprocurement', e)
        fn.session_log('cy_eprocurement', notice_count, 'Script error')
    except:
        pass
    raise e
finally:
    page_main.quit()
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("europe")