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
SCRIPT_NAME = "br_balneariocamboriu"
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
    notice_data.buyer = 'Prefeitura de Balneário Camboriú'
    notice_data.buyer_internal_id = '7775788'

    try:
        published_date = page_main.find_element(By.XPATH, '/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr['+str(tender_html_element)+']/td/a/table/tbody/tr[2]/td[1]').text
        published_date = re.findall('\d+/\d+/\d{4}', published_date)[0]
        notice_data.published_date = datetime.strptime(published_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr['+str(tender_html_element)+']/td/a/table/tbody/tr[1]/td[2]').text
        notice_data.title_en = notice_data.title_en.split(':')[1].strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        end_date = page_main.find_element(By.XPATH, '/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr['+str(tender_html_element)+']/td/a/table/tbody/tr[2]/td[3]').text
        end_date = re.findall('\d+/\d+/\d{4}', end_date)[0]
        notice_data.end_date = datetime.strptime(end_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.reference = page_main.find_element(By.XPATH, '/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr['+str(tender_html_element)+']/td/a/table/tbody/tr[1]/td[1]').text
        notice_data.reference = notice_data.reference.split(':')[1].strip()
    except:
        pass

    try:
    notice_data.notice_url = page_main.find_element(By.XPATH,"/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr["+str(tender_html_element)+"]/td/a").get_attribute('href')
    fn.load_page(page_details, notice_data.notice_url)
        try:
            submit = WebDriverWait(page_details, 30).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/div[2]/button[3]')))
            page_details.execute_script("arguments[0].click();",submit) 
            submit = WebDriverWait(page_details, 30).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/div[3]/p[2]/a')))
            page_details.execute_script("arguments[0].click();",submit)
        except:
            pass
        try:
            try:
                notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/main/div/div/div[2]/article'))).get_attribute('outerHTML')
                print(notice_data.notice_text)
            except:
                page_details.refresh()
                notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/main/div/div/div[2]/article'))).get_attribute('outerHTML')
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
    th = date.today() - timedelta(365)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.balneariocamboriu.sc.gov.br/licitacoes.cfm'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)

    submit = WebDriverWait(page_main, 30).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/div[2]/button[3]')))
    page_main.execute_script("arguments[0].click();",submit) 
    submit = WebDriverWait(page_main, 30).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/div[3]/p[2]/a')))
    page_main.execute_script("arguments[0].click();",submit) 

    try:
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr[1]/td/a/table/tbody/tr[2]/td[1]'))).text
    except:
        page_main.refresh()
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/main/div/div/div[2]/table[2]/tbody/tr[1]/td/a/table/tbody/tr[2]/td[1]'))).text
    try:
        submit = WebDriverWait(page_main, 30).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/button')))
        page_main.execute_script("arguments[0].click();",submit)
    except:
        pass

    rows = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/main/div/div/div[2]/table[2]/tbody'))).find_elements(By.CSS_SELECTOR, 'a')
    length = len(rows)
    for tender_html_element in range(1,length+1):
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
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("latin")

