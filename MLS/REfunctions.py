import pandas as pd
from datetime import datetime, timedelta

# drop columns
def drop_col(df):
    columns_to_drop = ['MLS #','Cat', 'County','HOA Fee', 'Lot Size Acres', 'Main Level Bedrooms', 'Main Level Bedrooms',	'Main Level Full Baths','Main Level Half Baths','Municipality','RATIO Close Price By List Price','RATIO Close Price By Original List Price' ]
    df =df.drop(columns = columns_to_drop)
    df.drop(df[df['Status'] == 'C/S'].index, inplace = True) 

# drop rows with no bathrooms or bedrooms
def drop_zero_bed_bath(df):
    df = df.dropna(subset=['Baths']) 
    df = df.dropna(subset=['Beds']) 
    df = df[df['Beds'] != 0]
    return df

# reassign datae and make it a datetime
def setdate(df):
    df['date'] = pd.to_datetime(df.loc[:,('Status Contractual Search Date')])
    del df['Status Contractual Search Date']   

# fix the "half bath" issue.  2 and 1 half bath is 2.1, 3 full and 2 halfs = 3.2baths
def fixbath(df):
    df['Baths']= [bath.replace('/','.') for bath in df.loc[:,('Baths')]]

def rename_cols(df):
    df = df.rename(columns={'Current Price':'price',
                                    'List Price':'list_price',
                                    'Price/SqFt':'pricePsqft', 
                                    'Original List Price':'ogPrice',
                                    'Structure Type':'home_type',
                                    'Building Name':'building_name',
                                    'Selling Office Name':'selling_office',
                                    'Total SQFT':'total_sqft',
                                    'Year Built':'year_built',
                                    'Zip Code':'zip',
                                    'Legal Subdivision':'subdivision',
                                    'Above Grade Finished SQFT':'above_grade_sqft',
                                    'List Agent Full Name':'list_agent',
                                    'Selling Agent Full Name':'selling_agent',
                                    'List Office Name':'office'})

# create a column that has a month and a year for sorting and charting
def create_date_cols(df):
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    df['year_month'] = df['date'].dt.strftime("%Y-%m")
    df['m_y_bin'] = df['year_month'].astype(str).str.cat(df['price_range'].astype(str), sep="_")


# make bins and baskets for price of house and for square footage
# bins =['$150k-$249k','$250k-$349k','$350k-$449k','$450k-$549k','$550k-$649k','$650k-749k','$750k-849k','$850k-$949k','$950k+']
def make_price_bins(df):
    # make price bins and baskets
    bins =['$150k-$249k','$250k-$349k','$350k-$449k','$450k-$549k','$550k-$649k','$650k-749k','$750k-849k','$850k-$949k','$950k+']
    price_basket = [149999,249999,349999,449999,549999,649999,749999,849999,949999,20000000]
    df['price_range']=pd.cut(df['price'], price_basket, labels=bins)
    return bins

def make_sqft_bins(df):
    # create column that bins the square feet
    sqft_bins =['A_0-1K','B_1.0K-1.5K','C_1.5k-2K','D_2K+']
    sqft_basket = [0,1000,1500,2000,20000]
    df['space_bin']=pd.cut(df['total_sqft'], sqft_basket, labels=sqft_bins)

# strip '$' signs and commas
def fix_nums(df):
    cols = ['price','list_price','pricePsqft', 'ogPrice','total_sqft','above_grade_sqft'] 

    for col in cols:
        df[col]=df.loc[:,col].str.strip('$').str.replace(',','').astype(float)

# Create another column that combines Active under Contract and Pending into one group CON
def fix_status(df):
    for index in df.index:
        if df.loc[index,'Status']=='A/C':
            df.loc[index,'Cat']='CON'
        elif df.loc[index,'Status']=='PND':
            df.loc[index,'Cat']='CON'
        elif df.loc[index,'Status']=='ACT':
            df.loc[index,'Cat']='ACT'
        elif df.loc[index,'Status']=='CLS':
            df.loc[index,'Cat']='CLS' 
            
def get_end_date(df):
    end_date =  df['date'].max()
    # print('THe End Date is',end_date)
    return end_date


# Get absorption rate for ast 30 days
def get_ab_rate(df):
    end_date =  df['date'].max()

    """put in a dataframe with Real Esate data it will figure out the latest date of a listing and subtract 30 days.
    and you will get out a tuple 
    """
    dt_start=pd.to_datetime(end_date - timedelta(days=30))
    dt_end=pd.to_datetime(df.date.max())
    mask_period = (df['date'] > dt_start) & (df['date'] <= dt_end)
    df_period = df.loc[mask_period]

    per_active_count = df_period[df_period.Cat == 'ACT'].Status.count()+1
    per_closed_count = df_period[df_period.Cat == 'CLS'].Status.count()+1
    per_contract_count = df_period[df_period.Cat == 'CON'].Status.count()+1

    total_absorbtion = float(round(per_closed_count/(per_active_count+per_contract_count),2)*100)

    months_of_inventory =float(round((per_active_count/per_closed_count),2))

    # print(total_absorbtion)
    return total_absorbtion,months_of_inventory,per_active_count,per_closed_count,per_contract_count,dt_start,dt_end


# find and asssign the absobtion rate and the months inventory for each price range.
def make_col_absorption(df):
    ab_dict_ab={}
    ab_dict_mon={}
    end_date =  df['date'].max()

    for price_bin in df.price_range.unique():
        df_price_bin = df[(df.price_range == price_bin)]
        absorbtion, months_inv,*r = get_ab_rate(df_price_bin)
        ab_dict_ab[price_bin]=absorbtion
        ab_dict_mon[price_bin]= months_inv
        
    df['absorb'] = df['price_range'].map(ab_dict_ab).astype(float)
    df['mon_inv'] = df['price_range'].map(ab_dict_mon).astype(float)


# create a function that groups by y_m (year_Month, i.e. 2020_5) and counts deals closed and assigns that number to the row.
#all closed deals in df

def make_monthly_closed(df):
    df_closed = df[df.Cat == 'CLS'] 
    grouped_list=[]
    bins =['$150k-$249k','$250k-$349k','$350k-$449k','$450k-$549k','$550k-$649k','$650k-749k','$750k-849k','$850k-$949k','$950k+']


    for slot in bins:
        df_slot = df_closed[(df_closed.price_range == slot)] 
        df_grouped_closed = df_slot[['m_y_bin','price']].groupby(['m_y_bin'],as_index=False).count()
        for i in range(len(df_grouped_closed)):
            grouped_list.append(df_grouped_closed['m_y_bin'][i])
            grouped_list.append(df_grouped_closed['price'][i])

    res_dct = {grouped_list[i]: grouped_list[i + 1] for i in range(0, len(grouped_list), 2)}
    df['monthly_closed'] = df['m_y_bin'].map(res_dct)

# grab only the last X days
def last_x_days(df, days):
    """put in a dataframe with Real Estate data it will figure out the latest date of a listing and subtract 30 days.
    and you will get out a tuple of (absorption rate, Months of Inventory)
    """
    end_date = df['date'].max()
    dt_start = pd.to_datetime(end_date - timedelta(days=days))
    dt_end = pd.to_datetime(df.date.max())
    mask_period = (df['date'] > dt_start) & (df['date'] <= dt_end)
    return df.loc[mask_period]

    