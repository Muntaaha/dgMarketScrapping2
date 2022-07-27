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
SCRIPT_NAME = "bo_licitaciones"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'Bolivia'
    notice_data.contact_country = 'Bolivia'
    notice_data.procurement_method = "Other"
    notice_data.language = "ES"
    notice_data.notice_type = 'spn'

    try:
        published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(8)').text
        published_date = re.findall('\d+-\d+-\d{4}', published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%m/%d/%Y').strftime('%Y/%m/%d')
        logging.info(notice_data.published_date)
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(4)').text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(9)').text
        notice_data.end_date = re.findall('\d+-\d+-\d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%m-%d-%Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3) b').text
    except:
        pass

    try:
        buyer = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text
        notice_data.buyer = buyer.replace(notice_data.reference,'').strip()
    except:
        pass

    try:
        EOS = tender_html_element.find_element(By.CSS_SELECTOR,'td:nth-of-type(7)').text
        EOS = EOS.split('Bs.')[1].strip()
        EOS = EOS.split('$us')[0].strip()
        EOS = EOS.replace('.','').strip()
        EOS = EOS.replace(',','.').strip()
        notice_data.est_cost = re.sub("[^\d\.]", "", EOS)
        notice_data.currency = "USD"
    except:
        pass

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(10) a").get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)
        
        try:
            notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/main/section/div/div/table/tbody'))).get_attribute('outerHTML')
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
    th = date.today() - timedelta(1400)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.licitaciones.com.bo/convocatorias-nacionales-1.html'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    for page_number in range(2,70):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/main/section/div/table/tbody/tr[2]/td[1]'))).text
        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/main/section/div/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[1:]:
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            url = 'https://www.licitaciones.com.bo/convocatorias-nacionales-'+str(page_number)+'.html'
            fn.load_page(page_main, url)
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/main/section/div/table/tbody/tr[2]/td[4]/a'),page_check))
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
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("south_america")

