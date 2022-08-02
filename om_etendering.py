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
SCRIPT_NAME = "om_etendering"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'Oman'
    notice_data.contact_country = 'Oman'
    notice_data.procurement_method = "Other"
    notice_data.language = "AR"
    notice_data.notice_type = "spn"

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/form/div[3]/div[5]/table/tbody[1]/tr['+str(tender_html_element)+']/td[3]').text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.reference = page_main.find_element(By.XPATH, '/html/body/form/div[3]/div[5]/table/tbody[1]/tr['+str(tender_html_element)+']/td[2]').text
    except:
        pass

    try:
        notice_data.buyer = page_main.find_element(By.XPATH, '/html/body/form/div[3]/div[5]/table/tbody[1]/tr['+str(tender_html_element)+']/td[3]').text
    except:
        pass

    try:
        page_main.find_element(By.XPATH, '/html/body/form/div[3]/div[5]/table/tbody[1]/tr['+str(tender_html_element)+']/td[7]/a').click()
        window_after = page_main.window_handles[1]
        page_main.switch_to.window(window_after)
        notice_data.notice_url = page_main.current_url
        print(notice_data.notice_url)
        try:
            notice_data.published_date = page_main.find_element(By.XPATH, '/html/body/form/div/div[3]/table/tbody/tr/td/div[4]/table/tbody/tr[1]/td[2]').text
            notice_data.published_date = re.findall('\d+-\d+-\d{4}', notice_data.published_date)[0]
            notice_data.published_date = datetime.strptime(notice_data.published_date, '%d-%m-%Y').strftime('%Y/%m/%d')
            logging.info(notice_data.published_date)
            print(notice_data.published_date)
        except:
            pass

        if notice_data.published_date is not None and notice_data.published_date < threshold:
            return

        try:
            notice_data.end_date = page_main.find_element(By.XPATH, '/html/body/form/div/div[3]/table/tbody/tr/td/div[4]/table/tbody/tr[1]/td[4]').text
            notice_data.end_date = re.findall('\d+-\d+-\d{4}', notice_data.end_date)[0]
            notice_data.end_date = datetime.strptime(notice_data.end_date, '%d-%m-%Y').strftime('%Y/%m/%d')
            print(notice_data.end_date)
        except:
            pass

        try:
            notice_data.notice_text += wait.until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div'))).get_attribute('outerHTML')
        except:
            pass

        page_main.switch_to.window(window_before)

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
wait = WebDriverWait(page_main, 20)
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://etendering.tenderboard.gov.om/product/publicDash?viewFlag=NewTenders#'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    window_before = page_main.window_handles[0]
    for page_number in range(1,5):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[3]/div[5]/table/tbody[1]/tr[1]/td[2]'))).text
        for tender_html_element in range(1,51):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            page_main.switch_to.window(window_before)
            wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[3]/div[5]/table/tbody[1]/tr[51]/td/table/tbody/tr/td[8]/a'))).click()
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/form/div[3]/div[5]/table/tbody[1]/tr[1]/td[2]'),page_check))
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
    output_xml_file.copyFinalXMLToServer("middle_east")

