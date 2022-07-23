import logging
import re
import time
import dateparser
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
SCRIPT_NAME = "co_politecnicojic"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'Colombia'
    notice_data.contact_country = 'Colombia'
    notice_data.procurement_method = "Other"
    notice_data.language = "ES"
    notice_data.notice_type = 'spn'
    notice_data.buyer = 'Politécnico Colombiano Jaime Isaza Cadavid'
    notice_data.buyer_internal_id = '7776689'

    try:
        notice_data.reference = page_main.find_element(By.CSS_SELECTOR, 'h2 a').text.strip()
    except:
        pass

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, 'h2 a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            end_date = page_details.find_element(By.XPATH, '/html/body/div[8]/div[5]/div/main/div[2]/div[2]/p[4]').text
            end_date = re.findall('\d+ \w{2} \w+ \w{2} \d{4}', end_date)[0]
            end_date = end_date.replace('de ','').strip()
            end_date = dateparser.parse(end_date, settings={'DATE_ORDER': 'DMY'})
            end_date = str(end_date)
            notice_data.end_date = datetime.strptime(end_date, '%Y-%m-%d %X').strftime('%Y/%m/%d')
        except:
            pass

        if notice_data.end_date is not None and notice_data.end_date < threshold:
            return

        try:
            notice_data.title_en = page_details.find_element(By.XPATH, '/html/body/div[8]/div[5]/div/main/div[2]/div[2]/p[1]').text.strip()
            notice_data.title_en = notice_data.title_en.split('OBJETO:')[1].strip()
            notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
        except:
            pass

        try:
            EOS = page_details.find_element(By.XPATH,'/html/body/div[8]/div[5]/div/main/div[2]/div[2]/p[3]').text
            EOS = EOS.replace('.','').strip()
            notice_data.est_cost = re.sub("[^\d\.]", "", EOS)
            notice_data.currency = 'USD'
        except:
            pass
        try:
            notice_text += wait.page_details.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[8]/div[5]/div/main/div[2]'))).get_attribute('outerHTML')
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
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    urls = ['https://www.politecnicojic.edu.co/convocatorias-contratacion/61-subasta-inversa',
           'https://www.politecnicojic.edu.co/convocatorias-contratacion/60-seleccion-minima-cuantia',
           'https://www.politecnicojic.edu.co/convocatorias-contratacion/59-seleccion-abreviada-de-menor-cuantia',
           'https://www.politecnicojic.edu.co/convocatorias-contratacion/58-licitacion-publica']
    logging.info('----------------------------------')
    for url in urls:
        fn.load_page(page_main, url)
        logging.info(url)
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[8]/div[5]/div/main/div[2]/div[2]/div/div/h2/a'))).text
        rows = WebDriverWait(page_main, 50).until(EC.presence_of_element_located((By.CSS_SELECTOR,'.blog'))).find_elements(By.CSS_SELECTOR, '.page-header')
        length = len(rows)

        for row_num in range(0,length):
            tender_html_element = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.blog'))).find_elements(By.CSS_SELECTOR, '.page-header')[row_num]
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.end_date is not None and  notice_data.end_date < threshold:
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

