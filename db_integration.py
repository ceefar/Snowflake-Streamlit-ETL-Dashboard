# db_integration.py

# ---- note ----

# normally this would be filled with all db queries, 
# but since using portolio mode and echo many queries are with their respective modules


# ---- imports ----

# for web app 
import streamlit as st
import snowflake.connector
# for datetime objects
import datetime


# ---- snowflake db setup ----

# initialize connection - uses st.experimental_singleton to only run once.
@st.experimental_singleton
def init_connection():
    return snowflake.connector.connect(**st.secrets["snowflake"])

conn = init_connection()

# perform get/fetch query - uses st.experimental_memo to only rerun when the query changes or after 10 min.
# ig with memo what they want you to do is pull all the data and just manipulate with python but meh
@st.experimental_memo(ttl=600)
def run_query(query):
    """ write me """
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


#def init_setup():
#    run_query("ALTER SESSION SET timestamp_output_format = 'YYYY-MM-DD HH24:MI:SS.FF'")
#    run_query("ALTER SESSION SET TIMEZONE = 'Europe/London'")






# ---- general query functions ----

# generally expected to be used in multiple pages/modules

def get_basic_dates(return_date:str) -> datetime: # actually returns datetime.date but might refactor
    """ 
    get current date, yesterdays date, the first date with valid data in the db
    """

    # big fan of using dictionaries for switch cases if you can't tell, this grabs the query based on the given passed parameter (e.g. current)
    what_date_dict = {"current":run_query("SELECT DATE(GETDATE())"), "yesterday":run_query("SELECT DATE(DATEADD(day,-1,GETDATE()))"),
                        "first":run_query("SELECT current_day FROM redshift_bizinsights ORDER BY current_day ASC LIMIT 1")}

    # if return date in dict do return else return sumnt else
    if return_date in what_date_dict:
        # run query from the dictionary based on given parameter, then unpack the result (as is nested (list(tuple(result))) as is a solo query)
        select_return_date = what_date_dict[return_date][0][0]
        return(select_return_date)
    else:
        return(None)


def get_day_before(set_date:datetime) -> datetime:
    """ returns the date before the given date, takes datetime (maybe also takes a string) """
    day_before = run_query(f"SELECT DATE(DATEADD(day, -1,'{set_date}'))")
    # unpack the query before sending
    return(day_before[0][0])


# ---- sales insights ----
# used primarily by given module, though not necessarily exclusively

def get_cups_sold_by_hour_one_store(store_name, current_day) -> tuple:
    """ moved to module for echo """
    cups_by_hour_query = f"SELECT COUNT(i.item_name) AS cupsSold, EXTRACT(HOUR FROM TO_TIMESTAMP(d.timestamp)) AS theHour, i.item_name FROM redshift_customeritems i inner join redshift_customerdata d on (i.transaction_id = d.transaction_id) WHERE store = '{store_name}' AND DATE(d.timestamp) = '{current_day}' GROUP BY d.timestamp, i.item_name"
    cups_by_hour = run_query(cups_by_hour_query)
    return(cups_by_hour)


def get_cups_sold_by_time_of_day(time_of_day_enum) -> tuple:
    """ write me """
    cups_sold_for_time_of_day_query = f"SELECT COUNT(i.item_name) AS cupsSold, i.item_name, d.time_of_day FROM redshift_customeritems i inner join redshift_customerdata d on (i.transaction_id = d.transaction_id) WHERE d.time_of_day = {time_of_day_enum} GROUP BY i.item_name, d.time_of_day ORDER BY i.item_name"
    cups_sold_for_time_of_day = run_query(cups_sold_for_time_of_day_query)
    #FIXME: replace the int/enum with string of the time of day (is just easier) 
    #TODO: use a for loop and .replace() for this??
    # print(cups_sold_for_time_of_day)
    return(cups_sold_for_time_of_day)


# ---- NEW app dashboard - store revenue breakdown ----

def get_stores_breakdown_revenue_via_bizi(store_name:str, i_want:str = "alltime", somedates:tuple = ("2022-06-07","2022-07-05")):
    """
    i_want = input parameter for which query you want returned,
    - alltime = sum of all total revenue 
    - alltimedates = revenue for the day with its date returned as tuple (day_revenue:decimal, date:datetime)
    - justdays = count of all valid days (for completeness)
    - weekofyear = just (unique) week numbers
    - thesedays = like just days, a count of valid days, but between two given dates and only for one store
    - datesavgrevenue = average revenue between two dates
    - avg cs for dates = average customer spend between dates
    - avg cs = average customer spend all time
    - avgcusts = average customers per day all time
    - avgcups = average coffees sold per day all time
    bizi meaning from biz insights table, potentially may cause slighly less complete data but will do for now
    """
    if i_want == "alltime":
        store_alltime_rev = run_query(f"SELECT SUM(total_revenue_for_day) FROM redshift_bizinsights WHERE store_name = '{store_name}'")
        return(store_alltime_rev[0][0])
    elif i_want == "alltimedates":
        store_alltime_datesrev = run_query(f"SELECT total_revenue_for_day, current_day FROM redshift_bizinsights WHERE store_name = '{store_name}'")
        return(store_alltime_datesrev) # list of tuples (decimal, datetime)
    elif i_want == "justdays":
        just_all_days_count = run_query(f"SELECT DISTINCT DATE(timestamp) FROM redshift_customerdata")
        return(len(just_all_days_count))
    elif i_want == "thesedays":
        just_all_days_count = run_query(f"SELECT DISTINCT DATE(timestamp) FROM redshift_customerdata WHERE store = '{store_name}' AND DATE(timestamp) BETWEEN '{somedates[0]}' AND '{somedates[1]}'")
        return(len(just_all_days_count))
    elif i_want == "weekofyear":
        just_week_of_year = run_query(f"SELECT DISTINCT WEEKOFYEAR(current_day) FROM redshift_bizinsights WHERE store_name = '{store_name}'")
        return(just_week_of_year)
    elif i_want == "datesavgrevenue":
        avg_rev_for_dates = run_query(f"SELECT SUM(total_revenue_for_day) FROM redshift_bizinsights WHERE store_name = '{store_name}' AND current_day BETWEEN '{somedates[0]}' AND '{somedates[1]}'")
        return(avg_rev_for_dates[0][0])    
    elif i_want == "avgcsfordates":
        avgcsfordates = run_query(f"SELECT AVG(avg_spend_per_customer_for_day) FROM redshift_bizinsights WHERE store_name = '{store_name}' AND current_day BETWEEN '{somedates[0]}' AND '{somedates[1]}'")
        return(avgcsfordates[0][0])
    elif i_want == "avgcs":
        avgcs = run_query(f"SELECT AVG(avg_spend_per_customer_for_day) FROM redshift_bizinsights WHERE store_name = '{store_name}'")
        return(avgcs[0][0])
    elif i_want == "avgcusts":
        avgcusts = run_query(f"SELECT AVG(total_customers_for_day) FROM redshift_bizinsights WHERE store_name = '{store_name}'")
        return(avgcusts[0][0])        
    elif i_want == "avgcups":
        avgcups = run_query(f"SELECT AVG(total_coffees_sold_for_day) FROM redshift_bizinsights WHERE store_name = '{store_name}'")
        return(avgcups[0][0])        
    else:
        return(0)
    