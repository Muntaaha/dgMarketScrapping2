import logging
import re
import time
from datetime import date, datetime, timedelta
from deep_translator import GoogleTranslator
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 20000
script_name = "bs_nib_bahamas"

notice_count = 0
output_xml_file = common.OutputXML.OutputXML(script_name)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    wait_detail = WebDriverWait(page_details, 20)
    

    notice_data.performance_country = 'Bahamas'
    notice_data.contact_country = 'Bahamas'
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.buyer = 'National Insurance Board (NIB)'
    notice_data.buyer_internal_id = '7785812'
    try:
        end_date = tender_html_element.find_element(By.CSS_SELECTOR, "td:nth-of-type(4) span").text
        try:
            try:
                end_date = re.findall('\w+ \d+, \d{4}',end_date)[0]
                end_date = end_date.replace(',','').strip()
            except:    
                end_date = re.findall('\w+ \d+\w+, \d{4}',end_date)[0]
                end_date = end_date.replace(',','').strip()
                end_date = end_date.replace('st','').strip()
                end_date = end_date.replace('nd','').strip()
                end_date = end_date.replace('rd','').strip()
                end_date = end_date.replace('th','').strip()
        except:
            try:    
                end_date = re.findall('\w+ \d+\w+ \d{4}',end_date)[0]
                end_date = end_date.replace('st','').strip()
                end_date = end_date.replace('nd','').strip()
                end_date = end_date.replace('rd','').strip()
                end_date = end_date.replace('th','').strip()
            except:
                end_date = re.findall('\w+ \d+ \d{4}',end_date)[0]
        notice_data.end_date =  datetime.strptime(end_date, '%B %d %Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.end_date is not None and  notice_data.end_date < threshold:
        return
    
    try:
        try:
            try:
                notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(3) p span").text
            except:
                notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(3) span").text
        except:
            notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(3)").text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        try:
            notice_data.address = tender_html_element.find_element(By.CSS_SELECTOR, "td:nth-of-type(2) span").text
        except:
            notice_data.address = tender_html_element.find_element(By.CSS_SELECTOR, "td:nth-of-type(2)").text
    except:
        pass

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(1) a").get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)
        
        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'//*[@id="content-container"]/div[2]/div[1]'))).text
            notice_data.notice_text = notice_data.notice_text.replace('Register Now!','')
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

th = date.today() - timedelta(1)
threshold = th.strftime('%Y/%m/%d')
logging.info("Scraping from or greater than: " + threshold)

try:
    url = 'https://www.nib-bahamas.com/_m1876/public-tenders'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    

    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[2]/div/div/div[1]/div/div[2]/div/div[2]/div/div[1]/div/div/table[2]/tbody/tr[2]/td[2]/span'))).text
    for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="content-holder"]/div/div[1]/div/div/table[2]/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[1:]:
        extract_and_save_notice(tender_html_element)
        if notice_count >= MAX_NOTICES:
            break

        if notice_data.end_date is not None and  notice_data.end_date < threshold:
            break         

    
    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log(script_name, notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log(script_name, e)
        fn.session_log(script_name, notice_count, 'Script error')
    except:
        pass
    raise e
finally:
    logging.info('finally')
    page_main.quit()
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("north_america")