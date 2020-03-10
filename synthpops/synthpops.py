import os
import numpy as np
import pylab as pl
import pandas as pd
import sciris as sc
from .config import datadir

def norm_dic(dic):
    """
    Return normalized dict.
    """
    total = np.sum([dic[i] for i in dic], dtype = float)
    if total == 0.0:
        return dic
    new_dic = {}
    for i in dic:
        new_dic[i] = float(dic[i])/total
    return new_dic

def get_gender_fraction_by_age_path(location, datadir=datadir):
    """ Return filepath for all Seattle Metro gender fractions by age bracket. """
    return os.path.join(datadir,'census','age distributions',location + '_gender_fraction_by_age_bracket.dat')

def read_gender_fraction_by_age_bracket(location, datadir=datadir):
    """ 
    Return dict of gender fractions by age bracket for all Seattle Metro.

    """
    f = get_gender_fraction_by_age_path(location, datadir=datadir)
    df = pd.read_csv(f)
    dic = {}
    dic['male'] = dict(zip(np.arange(len(df)),df.fraction_male))
    dic['female'] = dict(zip(np.arange(len(df)),df.fraction_female))
    return dic

def get_age_bracket_distr_path(location, datadir=datadir):
    """ Return filepath for age distribution by age brackets. """
    return os.path.join(datadir,'census','age distributions',location + '_age_bracket_distr.dat')


def read_age_bracket_distr(location, datadir=datadir):
    """
    Return dict of age distribution by age brackets. 

    """

    f = get_age_bracket_distr_path(location, datadir=datadir)
    df = pd.read_csv(f)
    return dict(zip(df.age_bracket,df.percent))

def get_age_brackets_from_df(ab_filepath):
    """
    Returns dict of age bracket ranges from ab_filepath.
    """
    ab_df = pd.read_csv(ab_filepath,header = None)
    dic = {}
    for index,row in enumerate(ab_df.iterrows()):
        age_min = row[1].values[0]
        age_max = row[1].values[1]
        dic[index] = np.arange(age_min,age_max+1)
    return dic

def get_age_by_brackets_dic(age_brackets):
    """
    Returns dict of age bracket by age.
    """
    age_by_brackets_dic = {}
    for b in age_brackets:
        for a in age_brackets[b]:
            age_by_brackets_dic[a] = b
    return age_by_brackets_dic

def get_contact_matrix(synpop_path,location,setting_code,num_agebrackets):
    """
    Return setting specific contact matrix for num_agebrackets age brackets. 
    For setting code M, returns an influenza weighted combination of the settings: H, S, W, R.
    """
    file_path = os.path.join(datadir,'SyntheticPopulations','asymmetric_matrices','data_' + setting_code + str(num_agebrackets),'M' + str(num_agebrackets) + '_' + location + '_' + setting_code + '.dat')
    return np.array(pd.read_csv(file_path,delimiter = ' ', header = None))

def get_contact_matrix_dic(location, datadir=datadir, num_agebrackets):
    """
    Return a dict of setting specific age mixing matrices. 
    """
    matrix_dic = {}
    for setting_code in ['H','S','W','R']:
        matrix_dic[setting_code] = get_contact_matrix(location, datadir=datadir,setting_code,num_agebrackets)
    return matrix_dic

def combine_matrices(matrix_dic,weights_dic,num_agebrackets):
    M = np.zeros((num_agebrackets,num_agebrackets))
    for setting_code in weights_dic:
        M += matrix_dic[setting_code] * weights_dic[setting_code]
    return M

def get_ages(synpop_path,location,num_agebrackets):
    """
    Return synthetic age counts for num_agebrackets age brackets.
    """
    file_path = os.path.join(datadir,'SyntheticPopulations','synthetic_ages','data_a85','a85_' + location + '.dat')
    df = pd.read_csv(file_path, delimiter = ' ', header = None)
    return dict(zip(df.iloc[:,0].values, df.iloc[:,1].values))

def get_ids_by_age_dic(age_by_id_dic):
    ids_by_age_dic = {}
    for i in age_by_id_dic:
        ids_by_age_dic.setdefault( age_by_id_dic[i], [])
        ids_by_age_dic[ age_by_id_dic[i] ].append(i)
    return ids_by_age_dic

def sample_single(distr):
    """
    Return a single sampled value from a distribution.
    """
    if type(distr) == dict:
        distr = norm_dic(distr)
        sorted_keys = sorted(distr.keys())
        sorted_distr = [distr[k] for k in sorted_keys]
        n = np.random.multinomial(1,sorted_distr,size = 1)[0]
        index = np.where(n)[0][0]
        return sorted_keys[index]
    elif type(distr) == np.ndarray:
        distr = distr / np.sum(distr)
        n = np.random.multinomial(1,distr,size = 1)[0]
        index = np.where(n)[0][0]
        return index

def sample_bracket(distr,brackets):
    """
    Return a sampled bracket from a distribution.
    """
    sorted_keys = sorted(distr.keys())
    sorted_distr = [distr[k] for k in sorted_keys]
    n = np.random.multinomial(1,sorted_distr, size = 1)[0]
    index = np.where(n)[0][0]
    return index

def sample_contact_age(age,age_brackets,age_by_brackets_dic,age_mixing_matrix):
    """
    Return age of contact by age of individual sampled from an age mixing matrix. 
    Age of contact is uniformly drawn from the age bracket sampled from the age mixing matrix.
    """
    b = age_by_brackets_dic[age]
    b_contact = sample_single(age_mixing_matrix[b,:])
    return np.random.choice(age_brackets[b_contact])

def sample_n_contact_ages(n_contacts,age,age_brackets,age_by_brackets_dic,age_mixing_matrix_dic,weights_dic,num_agebrackets=18):
    """
    Return n_contacts sampled from an age mixing matrix. Combines setting specific weights to create an age mixing matrix 
    from which contact ages are sampled.

    For school closures or other social distancing methods, reduce n_contacts and the weights of settings that should be affected.
    """
    age_mixing_matrix = combine_matrices(age_mixing_matrix_dic,weights_dic,num_agebrackets)
    contact_ages = []
    for i in range(n_contacts):
        contact_ages.append( sample_contact_age(age,age_brackets,age_by_brackets_dic,age_mixing_matrix) )
    return contact_ages

def get_n_contact_ids_by_age(contact_ids_by_age_dic,contact_ages,age_brackets,age_by_brackets_dic):
    """
    Return ids of n_contacts sampled from an age mixing matrix, where potential contacts are chosen from a list of contact ids by age
    """

    contact_ids = set()
    for contact_age in contact_ages:
        if len(contact_ids_by_age_dic[contact_age]) > 0:
            contact_id = np.choice( contact_ids_by_age_dic[contact_age] )
        else:
            b_contact = age_by_brackets_dic[contact_age]
            potential_contacts = []
            for a in age_brackets[b_contact]:
                potential_contacts += contact_ids_by_age_dic[a]
            contact_id = np.choice( potential_contacts )
        contact_ids.add(contact_id)
    return contact_ids

def get_age_sex(gender_fraction_by_age,age_bracket_distr,age_by_brackets,age_brackets,min_age=0, max_age=99, age_mean=40, age_std=20):
    '''
    Define age-sex distributions.
     
    '''
    try:
        b = sample_bracket(age_bracket_distr,age_brackets)
        age = np.random.choice(age_brackets[b])
        sex = np.random.binomial(1, gender_fraction_by_age['male'][b])
        return age, sex
    except:
        sex = pl.randint(2) # Define female (0) or male (1) -- evenly distributed
        age = pl.normal(age_mean, age_std) # Define age distribution for the crew and guests
        age = pl.median([min_age, age, max_age]) # Normalize
        return age, sex

def get_mortality_rates_filepath(path):
    return os.path.join(path,'mortality_rates_by_age_bracket.dat')


def get_mortality_rates_by_age_bracket(filepath):
    df = pd.read_csv(filepath)
    return dict(zip(df.age_bracket,df.rate))


def get_mortality_rates_by_age(mortality_rate_by_age_bracket,mortality_age_brackets):
    mortality_rates = {}
    for b in mortality_rate_by_age_bracket:
        for a in mortality_age_brackets[b]:
            mortality_rates[a] = mortality_rate_by_age_bracket[b]
    return mortality_rates


def calc_death(person_age,mortality_rates):
    # return np.random.binomial(1,mortality_rates[person_age])
    return mortality_rates[person_age]