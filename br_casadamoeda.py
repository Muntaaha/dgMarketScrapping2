import logging
import re
import time
from datetime import date, datetime, timedelta
# from deep_translator import GoogleTranslator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 2000
SCRIPT_NAME = "br_casadamoeda"
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
    notice_data.buyer = ''
    notice_data.buyer_internal_id = ''

    try:
        notice_data.end_date = page_main.find_element(By.XPATH, '/html/body/div/ul/li['+str(tender_html_element)+']/p[4]').text
        notice_data.end_date = re.findall('\d+/\d+/\d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        pass


    if notice_data.end_date is not None and notice_data.end_date < threshold:
        return

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/div/ul/li['+str(tender_html_element)+']/h2').text
        # notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = page_main.find_element(By.XPATH, '/html/body/div/ul/li['+str(tender_html_element)+']/p[2]').text
        notice_data.reference = notice_data.reference.split('Edital:')[1].strip()
        print(notice_data.reference)
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
    th = date.today() - timedelta(365)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.casadamoeda.gov.br/portal/negocios/licitacoes/audiencia-publica-e-outros.html'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    page_main.switch_to.frame('iframe')
    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/ul/li[1]/h2'))).text
    
    rows = len(wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div/ul'))).find_elements(By.CSS_SELECTOR, '.obs'))

    for tender_html_element in range(1, rows+1):
        extract_and_save_notice(tender_html_element)
        if notice_count >= MAX_NOTICES:
            break

        if notice_data.end_date is not None and  notice_data.end_date < threshold:
            break

                
    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    # fn.session_log(SCRIPT_NAME, notice_count, 'XML uploaded')
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

