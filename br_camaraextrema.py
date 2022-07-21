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
SCRIPT_NAME = "br_camaraextrema"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'Brazil'
    notice_data.contact_country = 'Brazil'
    notice_data.procurement_method = "Other"
    notice_data.language = "PT"
    notice_data.notice_type = 'spn'
    notice_data.buyer = 'CÂMARA MUNICIPAL DE EXTREMA'
    notice_data.buyer_internal_id = '7782850'

    try:
        end_date = tender_html_element.find_element(By.CSS_SELECTOR, '.processos div:nth-of-type(4) p').text
        end_date = re.findall('\d+/\d+/\d{4}', end_date)[0]
        notice_data.end_date = datetime.strptime(end_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        pass


    if notice_data.end_date is not None and notice_data.end_date < threshold:
        return

    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR, '.objeto').text
        notice_data.title_en = title_en.split('Objeto:')[1].strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, '.processos div:nth-of-type(1) p').text.strip()
    except:
        pass

    try:
        notice_data.resource_url = tender_html_element.find_element(By.CSS_SELECTOR, '.processos a').get_attribute('href')
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
    url = 'http://www.camaraextrema.mg.gov.br/licitacoes/'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    for page_number in range(2,14):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/main/section[2]/article[1]/h3'))).text

        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/main/section[2]'))).find_elements(By.CSS_SELECTOR, '.box'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.end_date is not None and  notice_data.end_date < threshold:
                break

        try:
            url = 'https://www.camaraextrema.mg.gov.br/licitacoes/page/'+str(page_number)+'/'
            fn.load_page(page_main, url)
            logging.info("Next page")
            WebDriverWait(page_main, 20).until_not(EC.text_to_be_present_in_element((By.XPATH, '/html/body/main/section[2]/article[1]/div/div[1]/p'),page_check))
        except:
            logging.info("No next page")
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

