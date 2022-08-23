import logging
import re
import time
from datetime import date, datetime, timedelta
import dateparser
from deep_translator import GoogleTranslator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 2000
SCRIPT_NAME = "au_nsw"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.notice_type = 'spn'
    notice_data.performance_country = "Australia"
    notice_data.contact_country = "Australia"

    data = page_main.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[4]/div['+str(tender_html_element)+']/div/div[2]/p').text
    try:
        notice_data.published_date = data.split('Published')[1].strip()
        notice_data.published_date = notice_data.published_date.split('Closes')[0].strip()
        notice_data.published_date = re.findall('\d+-\w+-\d{4}', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%d-%b-%Y').strftime('%Y/%m/%d')
    except:
        pass

    if notice_data.published_date is not None and notice_data.published_date < threshold:
        return

    try:
        notice_data.end_date = data.split('Closes')[1].strip()
        notice_data.end_date = notice_data.end_date.split('Category')[0].strip()
        notice_data.end_date = re.findall('\d+-\w+-\d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%d-%b-%Y').strftime('%Y/%m/%d')
    except:
        pass

    try:
        notice_data.reference = data.split('RFT ID')[1].strip()
        notice_data.reference = notice_data.reference.split('RFT Type')[0].strip()
    except:
        pass

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[4]/div['+str(tender_html_element)+']/div/div[1]/div/div[2]/h2/a').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.buyer = data.split('Agency')[1].strip()
        try:
            notice_data.buyer = notice_data.buyer.split('\n')[0].strip()
        except:
            pass
    except:
        pass

    try:
        notice_data.notice_url = page_main.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[4]/div['+str(tender_html_element)+']/div/div[1]/div/div[2]/h2/a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[2]'))).get_attribute('outerHTML')
        except:
            pass

    except:
        notice_data.notice_url = url

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
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://www.tenders.nsw.gov.au/?filterBy=published&category=&keyword=&startRow=0&orderBy=Publish%20Date%20%2D%20Descending%27&event=public%2ERFT%2Elist&ResultsPerPage=20'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    each_page = 0
    for page_number in range(8):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div[2]/div[4]/div[1]/div/div[1]/div/div[2]/h2/a'))).text
        for tender_html_element in range(1,16):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            each_page += 20
            url = 'https://www.tenders.nsw.gov.au/?filterBy=published&category=&keyword=&startRow='+str(each_page)+'&orderBy=Publish%20Date%20%2D%20Descending%27&event=public%2ERFT%2Elist&ResultsPerPage=20'+str(page_number)
            fn.load_page(page_main, url)
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div[2]/div[2]/div[4]/div[1]/div/div[1]/div/div[2]/h2/a'),page_check))
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
    output_xml_file.copyFinalXMLToServer("bd_team")

