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
SCRIPT_NAME = "br_bac_eb_mil"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'Brazil'
    notice_data.contact_country = 'Brazil'
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.buyer = 'BRAZILIAN ARMY COMMISSION'
    notice_data.buyer_internal_id = '7786023'

    try:
        published_date = page_main.find_element(By.XPATH, '/html/body/form/div/table/tbody/tr/td/table/tbody/tr['+str(tender_html_element)+']/td[2]').text
        published_date = re.findall('\d+/\d+/\d{4}', published_date)[0]
        notice_data.published_date = datetime.strptime(published_date, '%m/%d/%Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        end_date = page_main.find_element(By.XPATH, '/html/body/form/div/table/tbody/tr/td/table/tbody/tr['+str(tender_html_element)+']/td[3]').text
        end_date = re.findall('\d+/\d+/\d{4}', end_date)[0]
        notice_data.end_date = datetime.strptime(end_date, '%m/%d/%Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/form/div/table/tbody/tr/td/table/tbody/tr['+str(tender_html_element+1)+']/td').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = page_main.find_element(By.XPATH, '/html/body/form/div/table/tbody/tr/td/table/tbody/tr['+str(tender_html_element)+']/td[1]/a').text.strip()
    except:
        pass

    try:
        check_link = page_main.find_element(By.XPATH, '/html/body/form/div/table/tbody/tr/td/table/tbody/tr['+str(tender_html_element)+']/td[1]/a').get_attribute('href')
        link_first_part = check_link.split(",")[0].strip()
        link_first_part = link_first_part.replace("javascript:openDocument(","").strip()
        link_first_part = link_first_part.replace("'","").strip()
        notice_data.resource_url = 'https://dakota.cebw.org/cebwWeb/Bids?action=showDocument&documentId='+link_first_part+'&documentType=TERM'
    except:
        pass

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
wait = WebDriverWait(page_main, 20)
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://bac.eb.mil.br/budgetary-quotation-in-progress-rfi'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    page_main.switch_to.frame('blockrandom')

    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div/table/tbody/tr/td/table/tbody/tr[2]/td[1]/a'))).text

    total_tenders = len(wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="body"]/table/tbody/tr/td/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr'))
    for tender_html_element in range(2,total_tenders+1,2):
        extract_and_save_notice(tender_html_element)
        if notice_count >= MAX_NOTICES:
            break

        if notice_data.published_date is not None and  notice_data.published_date < threshold:
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
    output_xml_file.copyFinalXMLToServer("latin")

