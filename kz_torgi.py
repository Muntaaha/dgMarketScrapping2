import logging
import re
import time
from datetime import date, datetime, timedelta
import dateparser
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
output_xml_file = common.OutputXML.OutputXML("kz_torgi")

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    wait_detail = WebDriverWait(page_details, 20)
    

    notice_data.performance_country = 'Kazakhstan'
    notice_data.contact_country = 'Kazakhstan'
    notice_data.procurement_method = "Other"
    notice_data.language = "RU"
    
    notice_data.notice_type = "spn"
            
    try:
        published_date = page_main.find_element(By.CSS_SELECTOR, "td:nth-of-type(1) nobr").text
        published_date = re.findall('\d+.\d+.\d{4}',published_date)[0]
        notice_data.published_date =  datetime.strptime(published_date, '%d.%m.%Y').strftime('%Y/%m/%d')
    except:
        logging.info('Published Date Error')
        pass

    if notice_data.published_date is not None and  notice_data.published_date < threshold:
        return


    try:
        title_en = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(2)").text
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(title_en)
    except:
        pass

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR,"td:nth-of-type(3) a").get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            end_date = page_details.find_element(By.XPATH, "/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/table/tbody/tr[6]/td[3]/em").text
            end_date = re.findall('\w+ \d{4}',end_date)[0]
            end_date = '30 ' + end_date
            end_date = dateparser.parse(end_date, settings={'DATE_ORDER': 'DMY'})
            end_date = str(end_date)
            end_date =  datetime.strptime(end_date, '%Y-%m-%d %X').strftime('%Y/%m/%d')
            if end_date.split('/')[1] == '1' or end_date.split('/')[1] == '1' or end_date.split('/')[1] == '3' or end_date.split('/')[1] == '5' or end_date.split('/')[1] == '7' or end_date.split('/')[1] == '8' or end_date.split('/')[1] == '10' or end_date.split('/')[1] == '12':
                day = '31'
            elif end_date.split('/')[1] == '2':
                day = '28'
            else:
                day = '30'
            year = end_date.split('/')[0]
            month = end_date.split('/')[1]
            notice_data.end_date = year+'/'+month+'/'+day
        except:
            pass
            
        try:
            notice_data.buyer = page_details.find_element(By.XPATH,"/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/table/tbody/tr[3]/td[3]/em").text
        except:
            pass

        try:
            notice_data.contact_email = page_details.find_element(By.XPATH, "/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/table/tbody/tr[7]/td[3]/a/u/font").text
        except:
            pass
        
        try:
            contact_phone = page_details.find_element(By.XPATH, "/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/table/tbody/tr[9]/td[3]/em/font").text
            contact_phone = contact_phone.replace('Т:','').strip()
            notice_data.contact_phone = contact_phone.split(',')[0].strip()
        except:
            pass
 
        
        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/table/tbody'))).text
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

th = date.today() - timedelta(1600)
threshold = th.strftime('%Y/%m/%d')
logging.info("Scraping from or greater than: " + threshold)

try:

    url = 'https://torgi.erg.kz/CommonInfoPages/%D0%90%D0%BD%D0%BE%D0%BD%D1%81%D1%8B%20%D0%BF%D0%BB%D0%B0%D0%BD%D0%B8%D1%80%D1%83%D0%B5%D0%BC%D1%8B%D1%85%20%D0%B7%D0%B0%D0%BA%D1%83%D0%BF%D0%BE%D0%BA%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%20%D0%B8%20%D1%83%D1%81%D0%BB%D1%83%D0%B3.aspx?Paged=TRUE&p_Created=20211220%2006%3a05%3a05&p_ID=420&PageFirstRow=61&&View={80D9A494-6A61-4C59-A005-4E3125605640}'  
    logging.info(url)
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    
    submit = WebDriverWait(page_main, 30).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div/div[2]/div/div[2]/input[2]')))
    page_main.execute_script("arguments[0].click();",submit)

    for page in range(15):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/div[1]/div[1]/table/tbody/tr/td/table/tbody/tr/td/div/table[1]/tbody/tr/td/table/tbody/tr[2]/td[1]/nobr'))).text
        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/div[1]/div[1]/table/tbody/tr/td/table/tbody/tr/td/div/table[1]/tbody/tr/td/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[1:]:
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            next_page = WebDriverWait(page_main, 50).until(EC.element_to_be_clickable((By.XPATH, '/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/div[1]/div[1]/table/tbody/tr/td/table/tbody/tr/td/div/table[2]/tbody/tr[3]/td/table/tbody/tr/td[3]/a')))
            page_main.execute_script("arguments[0].click();",next_page)
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/form/div[8]/div/div[3]/div/div[2]/div/div/div/div[4]/div/div/table/tbody/tr/td/div/div/div[1]/div[1]/table/tbody/tr/td/table/tbody/tr/td/div/table[1]/tbody/tr/td/table/tbody/tr[2]/td[1]/nobr'),page_check))
            logging.info("Next Page")
        except:
            logging.info("No Next Page")
            break


    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log('kz_torgi', notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log('kz_torgi', e)
        fn.session_log('kz_torgi', notice_count, 'Script error')
    except:
        pass
    raise e
finally:
    page_main.quit()
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("cis")