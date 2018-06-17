import gc
from pprint import pprint

import pandas as pd
import numpy as np

import pathos.multiprocessing as mp

from sklearn.decomposition import TruncatedSVD

import lightgbm as lgb

from cv import run_cv_model
from utils import print_step, rmse, clean_text
from cache import get_data, is_in_cache, load_cache, save_in_cache


params = {'learning_rate': 0.03,
          'application': 'regression',
          'num_leaves': 250,
          'verbosity': -1,
          'metric': 'rmse',
          'data_random_seed': 3,
          'bagging_fraction': 0.8,
          'feature_fraction': 0.1,
          'nthread': 16, #max(mp.cpu_count() - 2, 2),
          'lambda_l1': 6,
          'lambda_l2': 6,
          'min_data_in_leaf': 40,
          'num_rounds': 4200,
          'verbose_eval': 100}

def runLGB(train_X, train_y, test_X, test_y, test_X2, params):
    print_step('Prep LGB')
    d_train = lgb.Dataset(train_X, label=train_y)
    d_valid = lgb.Dataset(test_X, label=test_y)
    watchlist = [d_train, d_valid]
    print_step('Train LGB')
    num_rounds = params['num_rounds']
    verbose_eval = params['verbose_eval']
    model = lgb.train(params,
                      train_set=d_train,
                      num_boost_round=num_rounds,
                      valid_sets=watchlist,
                      verbose_eval=verbose_eval)
    print_step('Feature importance')
    pprint(sorted(list(zip(model.feature_importance(), train_X.columns)), reverse=True))
    print_step('Predict 1/2')
    pred_test_y = model.predict(test_X)
    print_step('Predict 2/2')
    pred_test_y2 = model.predict(test_X2)
    return pred_test_y, pred_test_y2


print('~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Importing Data 1/18')
train, test = get_data()

print('~~~~~~~~~~~~~~~')
print_step('Subsetting')
target = train['deal_probability']
train_id = train['item_id']
test_id = test['item_id']
train.drop(['deal_probability', 'item_id'], axis=1, inplace=True)
test.drop(['item_id'], axis=1, inplace=True)

print('~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Importing Data 2/18')
train_fe, test_fe = load_cache('data_with_fe')

print_step('Importing Data 3/18 1/4')
train_img, test_img = load_cache('img_data')
print_step('Importing Data 3/18 2/4')
cols = ['img_size_x', 'img_size_y', 'img_file_size', 'img_mean_color', 'img_dullness_light_percent', 'img_dullness_dark_percent', 'img_blur', 'img_blue_mean', 'img_green_mean', 'img_red_mean', 'img_blue_std', 'img_green_std', 'img_red_std', 'img_average_red', 'img_average_green', 'img_average_blue', 'img_average_color', 'img_sobel00', 'img_sobel10', 'img_sobel20', 'img_sobel01', 'img_sobel11', 'img_sobel21', 'img_kurtosis', 'img_skew', 'thing1', 'thing2']
train_img = train_img[cols].fillna(0)
test_img = test_img[cols].fillna(0)
print_step('Importing Data 3/18 3/4')
train_fe = pd.concat([train_fe, train_img], axis=1)
print_step('Importing Data 3/18 4/4')
test_fe = pd.concat([test_fe, test_img], axis=1)

print_step('Importing Data 4/18 1/4')
# HT: https://www.kaggle.com/jpmiller/russian-cities/data
# HT: https://www.kaggle.com/jpmiller/exploring-geography-for-1-5m-deals/notebook
locations = pd.read_csv('city_latlons.csv')
print_step('Importing Data 4/18 2/4')
train_fe = train_fe.merge(locations, how='left', left_on='city', right_on='location')
print_step('Importing Data 4/18 3/4')
test_fe = test_fe.merge(locations, how='left', left_on='city', right_on='location')
print_step('Importing Data 4/18 4/4')
train_fe.drop('location', axis=1, inplace=True)
test_fe.drop('location', axis=1, inplace=True)

print_step('Importing Data 5/18 1/3')
region_macro = pd.read_csv('region_macro.csv')
print_step('Importing Data 5/18 2/3')
train_fe = train_fe.merge(region_macro, how='left', on='region')
print_step('Importing Data 5/18 3/3')
test_fe = test_fe.merge(region_macro, how='left', on='region')

print_step('Importing Data 6/18 1/3')
train_entity, test_entity = load_cache('price_entity_embed')
print_step('Importing Data 6/18 2/3')
train_fe = pd.concat([train_fe, train_entity], axis=1)
print_step('Importing Data 6/18 3/3')
test_fe = pd.concat([test_fe, test_entity], axis=1)

print_step('Importing Data 7/18 1/5')
train_active_feats, test_active_feats = load_cache('active_feats')
train_active_feats.fillna(0, inplace=True)
test_active_feats.fillna(0, inplace=True)
print_step('Importing Data 7/18 2/5')
train_fe = pd.concat([train_fe, train_active_feats], axis=1)
print_step('Importing Data 7/18 3/5')
test_fe = pd.concat([test_fe, test_active_feats], axis=1)
print_step('Importing Data 7/18 4/5')
train_fe['user_items_per_day'] = train_fe['n_user_items'] / train_fe['user_num_days']
test_fe['user_items_per_day'] = test_fe['n_user_items'] / test_fe['user_num_days']
train_fe['img_size_ratio'] = train_fe['img_file_size'] / (train_fe['img_size_x'] * train_fe['img_size_y'])
test_fe['img_size_ratio'] = test_fe['img_file_size'] / (test_fe['img_size_x'] * test_fe['img_size_y'])
print_step('Importing Data 7/18 5/5')
train_fe.drop('user_id', axis=1, inplace=True)
test_fe.drop('user_id', axis=1, inplace=True)

print_step('Importing Data 8/18 1/8')
train, test = get_data()
print_step('Importing Data 8/18 2/8')
train_nima, test_nima = load_cache('img_nima')
print_step('Importing Data 8/18 3/8')
train = train.merge(train_nima, on = 'image', how = 'left')
print_step('Importing Data 8/18 4/8')
test = test.merge(test_nima, on = 'image', how = 'left')
print_step('Importing Data 7/18 5/8')
cols = ['mobile_mean', 'mobile_std', 'inception_mean', 'inception_std',
        'nasnet_mean', 'nasnet_std']
train_fe[cols] = train[cols].fillna(0)
test_fe[cols] = test[cols].fillna(0)
print_step('Importing Data 8/18 6/8')
train_nima, test_nima = load_cache('img_nima_softmax')
print_step('Importing Data 8/18 7/8')
train = train[['item_id', 'image']].merge(train_nima, on = 'image', how = 'left')
test = test[['item_id', 'image']].merge(test_nima, on = 'image', how = 'left')
print_step('Importing Data 8/18 8/8')
cols = [x + '_' + str(y) for x in ['mobile', 'inception', 'nasnet'] for y in range(1, 11)]
train_fe[cols] = train[cols].fillna(0)
test_fe[cols] = test[cols].fillna(0)

print_step('Importing Data 9/18 1/20')
train_nasnet, test_nasnet = load_cache('nasnet')
print_step('Importing Data 9/18 2/20')
train_fe = pd.concat([train_fe, train_nasnet], axis=1)
print_step('Importing Data 9/18 3/20')
test_fe = pd.concat([test_fe, test_nasnet], axis=1)
print_step('Importing Data 9/18 4/20')
train_fe.drop('image', axis=1, inplace=True)
test_fe.drop('image', axis=1, inplace=True)
print_step('Importing Data 9/18 5/20')
train_xception, test_xception = load_cache('xception')
print_step('Importing Data 9/18 6/20')
train_fe = pd.concat([train_fe, train_xception], axis=1)
print_step('Importing Data 9/18 7/20')
test_fe = pd.concat([test_fe, test_xception], axis=1)
print_step('Importing Data 9/18 8/20')
train_fe.drop('image', axis=1, inplace=True)
test_fe.drop('image', axis=1, inplace=True)
print_step('Importing Data 9/18 9/20')
train_inception_resnet_v2, test_inception_resnet_v2 = load_cache('inception_resnet_v2')
print_step('Importing Data 9/18 10/20')
train_fe = pd.concat([train_fe, train_inception_resnet_v2], axis=1)
print_step('Importing Data 9/18 11/20')
test_fe = pd.concat([test_fe, test_inception_resnet_v2], axis=1)
print_step('Importing Data 9/18 12/20')
train_fe.drop('image', axis=1, inplace=True)
test_fe.drop('image', axis=1, inplace=True)
print_step('Importing Data 9/18 13/20')
del train, test, train_nima, test_nima, train_xception, test_xception
del train_nasnet, test_nasnet, train_inception_resnet_v2, test_inception_resnet_v2
gc.collect()
print_step('Importing Data 9/18 14/20')
train_fe['img_xception_inception_agree'] = (train_fe['xception_top_1'] == train_fe['inception_resnet_v2_top_1']).astype(int)
test_fe['img_xception_inception_agree'] = (test_fe['xception_top_1'] == test_fe['inception_resnet_v2_top_1']).astype(int)
print_step('Importing Data 9/18 15/20')
train_fe['img_nasnet_inception_agree'] = (train_fe['nasnet_top_1'] == train_fe['inception_resnet_v2_top_1']).astype(int)
test_fe['img_nasnet_inception_agree'] = (test_fe['nasnet_top_1'] == test_fe['inception_resnet_v2_top_1']).astype(int)
print_step('Importing Data 9/18 16/20')
train_fe['img_xception_nasnet_agree'] = (train_fe['xception_top_1'] == train_fe['nasnet_top_1']).astype(int)
test_fe['img_xception_nasnet_agree'] = (test_fe['xception_top_1'] == test_fe['nasnet_top_1']).astype(int)
print_step('Importing Data 9/18 17/20')
train_fe['img_all_agree'] = (train_fe['img_xception_nasnet_agree'] & train_fe['img_nasnet_inception_agree'] & train_fe['img_xception_inception_agree']).astype(int)
test_fe['img_all_agree'] = (test_fe['img_xception_nasnet_agree'] & test_fe['img_nasnet_inception_agree'] & test_fe['img_xception_inception_agree']).astype(int)
print_step('Importing Data 9/18 18/20')
train_fe['img_mean_label_score'] = np.mean([train_fe['xception_prob'], train_fe['inception_resnet_v2_prob'], train_fe['nasnet_prob']], axis=0)
test_fe['img_mean_label_score'] = np.mean([test_fe['xception_prob'], test_fe['inception_resnet_v2_prob'], test_fe['nasnet_prob']], axis=0)
print_step('Importing Data 9/18 19/20')
train_fe['img_std_label_score'] = np.std([train_fe['xception_prob'], train_fe['inception_resnet_v2_prob'], train_fe['nasnet_prob']], axis=0)
test_fe['img_std_label_score'] = np.std([test_fe['xception_prob'], test_fe['inception_resnet_v2_prob'], test_fe['nasnet_prob']], axis=0)
print_step('Importing Data 9/18 20/20')
train_fe.drop(['xception_top_1', 'nasnet_top_1', 'inception_resnet_v2_top_1'], axis=1, inplace=True)
test_fe.drop(['xception_top_1', 'nasnet_top_1', 'inception_resnet_v2_top_1'], axis=1, inplace=True)


print_step('Importing Data 10/18 1/2')
train_ridge, test_ridge = load_cache('tfidf_ridges')
print_step('Importing Data 10/18 2/2')
cols = [c for c in train_ridge.columns if 'svd' in c or 'tfidf' in c]
train_fe[cols] = train_ridge[cols]
test_fe[cols] = test_ridge[cols]


EMBEDDING_FILE = 'cache/avito_fasttext_300d.txt'
EMBED_SIZE = 300
NCOMP = 20

def text_to_embedding(text):
    mean = np.mean([embeddings_index.get(w, np.zeros(EMBED_SIZE)) for w in text.split()], axis=0)
    if mean.shape == ():
        return np.zeros(EMBED_SIZE)
    else:
        return mean

print_step('Importing Data 11/18 1/3')
if not is_in_cache('avito_fasttext_300d'):
    print_step('Embedding 1/5')
    train, test = get_data()

    print_step('Embedding 1/5')
    def get_coefs(word, *arr): return word, np.asarray(arr, dtype='float32')
    embeddings_index = dict(get_coefs(*o.rstrip().rsplit(' ')) for o in open(EMBEDDING_FILE))

    print_step('Embedding 2/5')
    train_embeddings = (train['title'].str.cat([
                            train['description'],
                        ], sep=' ', na_rep='')
                        .astype(str)
                        .fillna('missing')
                        .apply(clean_text)
                        .apply(text_to_embedding))

    print_step('Embedding 3/5')
    test_embeddings = (test['title'].str.cat([
                            test['description'],
                        ], sep=' ', na_rep='')
                        .astype(str)
                        .fillna('missing')
                        .apply(clean_text)
                        .apply(text_to_embedding))

    print_step('Embedding 4/5')
    train_embeddings_df = pd.DataFrame(train_embeddings.values.tolist(),
                                       columns = ['embed' + str(i) for i in range(EMBED_SIZE)])
    print_step('Embedding 5/5')
    test_embeddings_df = pd.DataFrame(test_embeddings.values.tolist(),
                                      columns = ['embed' + str(i) for i in range(EMBED_SIZE)])
    print_step('Caching...')
    save_in_cache('avito_fasttext_300d', train_embeddings_df, test_embeddings_df)
else:
    train_embeddings_df, test_embeddings_df = load_cache('avito_fasttext_300d')

print_step('Importing Data 11/18 2/3')
train_fe = pd.concat([train_fe, train_embeddings_df], axis=1)
print_step('Importing Data 11/18 3/3')
test_fe = pd.concat([test_fe, test_embeddings_df], axis=1)


print('~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Converting to category')
train_fe['image_top_1'] = train_fe['image_top_1'].astype('str').fillna('missing')
test_fe['image_top_1'] = test_fe['image_top_1'].astype('str').fillna('missing')
cat_cols = ['region', 'city', 'parent_category_name', 'category_name', 'cat_bin',
            'param_1', 'param_2', 'param_3', 'user_type', 'image_top_1', 'day_of_week',
            'img_average_color', 'nasnet_top_1', 'xception_top_1', 'inception_resnet_v2_top_1']
for col in train_fe.columns:
    print(col)
    if col in cat_cols:
        train_fe[col] = train_fe[col].fillna('missing').astype('category')
        test_fe[col] = test_fe[col].fillna('missing').astype('category')
    else:
        train_fe[col] = train_fe[col].fillna(0).astype(np.float64)
        test_fe[col] = test_fe[col].fillna(0).astype(np.float64)


print('~~~~~~~~~~~~~~~~~~~~~~')
print_step('Pre-flight checks')
for col in train_fe.columns:
    print('##')
    print(col)
    print('-')
    print(train_fe[col].values)
    print('-')
    print(test_fe[col].values)
    print('-')
print('-')


print('~~~~~~~~~~~~')
print_step('Run LGB')
print(train_fe.shape)
print(test_fe.shape)
results = run_cv_model(train_fe, test_fe, target, runLGB, params, rmse, 'base_lgb')
import pdb
pdb.set_trace()

print('~~~~~~~~~~')
print_step('Cache')
save_in_cache('base_lgb', pd.DataFrame({'base_lgb': results['train']}),
                          pd.DataFrame({'base_lgb': results['test']}))

print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Prepping submission file')
submission = pd.DataFrame()
submission['item_id'] = test_id
submission['deal_probability'] = results['test'].clip(0.0, 1.0)
submission.to_csv('submit/submit_base_lgb.csv', index=False)

print('~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Importing Data 12/18')
drops = [x + '_' + str(y) for x in ['mobile', 'inception', 'nasnet'] for y in range(1, 11)] + \
        ['img_size_ratio', 'times_put_up_min', 'times_put_up_max'] + \
        ['embed' + str(i) for i in range(EMBED_SIZE)]
train_fe.drop(drops, axis=1, inplace=True)
test_fe.drop(drops, axis=1, inplace=True)

print_step('Embedding SVD 1/4')
svd = TruncatedSVD(n_components=NCOMP, algorithm='arpack')
svd.fit(train_embeddings_df)
print_step('Embedding SVD 2/4')
train_svd = pd.DataFrame(svd.transform(train_embeddings_df))
print_step('Embedding SVD 3/4')
test_svd = pd.DataFrame(svd.transform(test_embeddings_df))
print_step('Embedding SVD 4/4')
train_svd.columns = ['svd_embed_'+str(i+1) for i in range(NCOMP)]
test_svd.columns = ['svd_embed_'+str(i+1) for i in range(NCOMP)]
train_fe = pd.concat([train_fe, train_svd], axis=1)
test_fe = pd.concat([test_fe, test_svd], axis=1)

print_step('Importing Data 13/18 1/2')
train_ridge, test_ridge = load_cache('tfidf_ridges')
print_step('Importing Data 13/18 2/2')
cols = [c for c in train_ridge.columns if 'ridge' in c]
train_fe[cols] = train_ridge[cols]
test_fe[cols] = test_ridge[cols]

print_step('Importing Data 14/18 1/3')
train_full_text_ridge, test_full_text_ridge = load_cache('full_text_ridge')
print_step('Importing Data 14/18 2/3')
train_fe['full_text_ridge'] = train_full_text_ridge['full_text_ridge']
print_step('Importing Data 14/18 3/3')
test_fe['full_text_ridge'] = test_full_text_ridge['full_text_ridge']

print_step('Importing Data 15/18 1/3')
train_complete_ridge, test_complete_ridge = load_cache('complete_ridge')
print_step('Importing Data 15/18 2/3')
train_fe['complete_ridge'] = train_complete_ridge['complete_ridge']
print_step('Importing Data 15/18 3/3')
test_fe['complete_ridge'] = test_complete_ridge['complete_ridge']

print_step('Importing Data 16/18 1/4')
train_pcat_ridge, test_pcat_ridge = load_cache('parent_cat_ridges')
print_step('Importing Data 16/18 2/4')
train_pcat_ridge = train_pcat_ridge[[c for c in train_pcat_ridge.columns if 'ridge' in c]]
test_pcat_ridge = test_pcat_ridge[[c for c in test_pcat_ridge.columns if 'ridge' in c]]
print_step('Importing Data 16/18 3/4')
train_fe = pd.concat([train_fe, train_pcat_ridge], axis=1)
print_step('Importing Data 16/18 4/4')
test_fe = pd.concat([test_fe, test_pcat_ridge], axis=1)

print_step('Importing Data 17/18 1/4')
train_rcat_ridge, test_rcat_ridge = load_cache('parent_regioncat_ridges')
print_step('Importing Data 17/18 2/4')
train_rcat_ridge = train_rcat_ridge[[c for c in train_rcat_ridge.columns if 'ridge' in c]]
test_rcat_ridge = test_rcat_ridge[[c for c in test_rcat_ridge.columns if 'ridge' in c]]
print_step('Importing Data 17/18 3/4')
train_fe = pd.concat([train_fe, train_rcat_ridge], axis=1)
print_step('Importing Data 17/18 4/4')
test_fe = pd.concat([test_fe, test_rcat_ridge], axis=1)

print_step('Importing Data 18/18 1/4')
train_catb_ridge, test_catb_ridge = load_cache('cat_bin_ridges')
print_step('Importing Data 18/18 2/4')
train_catb_ridge = train_catb_ridge[[c for c in train_catb_ridge.columns if 'ridge' in c]]
test_catb_ridge = test_catb_ridge[[c for c in test_catb_ridge.columns if 'ridge' in c]]
print_step('Importing Data 18/18 3/4')
train_fe = pd.concat([train_fe, train_catb_ridge], axis=1)
print_step('Importing Data 18/18 4/4')
test_fe = pd.concat([test_fe, test_catb_ridge], axis=1)

print('~~~~~~~~~~~~~~~~~~')
print_step('Run Ridge LGB')
print(train_fe.shape)
print(test_fe.shape)
params['num_rounds'] = 3100
results = run_cv_model(train_fe, test_fe, target, runLGB, params, rmse, 'ridge_lgb')
import pdb
pdb.set_trace()

print('~~~~~~~~~~')
print_step('Cache')
save_in_cache('ridge_lgb', pd.DataFrame({'ridge_lgb': results['train']}),
                           pd.DataFrame({'ridge_lgb': results['test']}))

print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Prepping submission file')
submission = pd.DataFrame()
submission['item_id'] = test_id
submission['deal_probability'] = results['test'].clip(0.0, 1.0)
submission.to_csv('submit/submit_ridge_lgb.csv', index=False)


# BASE
# [2018-06-17 02:15:35.160780] base_lgb cv scores : [0.2180584840223271, 0.2173285470396579, 0.21730824294582546, 0.21708803739182905, 0.21764331398813264]
# [2018-06-17 02:15:35.160849] base_lgb mean cv score : 0.21748532507755441
# [2018-06-17 02:15:35.160952] base_lgb std cv score : 0.0003368223898769227


# RIDGE LGB
# [2018-06-15 04:56:50.288476] ridge_lgb cv scores : [0.2147783829876306, 0.21395614971673593, 0.2138701184179281, 0.21380657669625333, 0.21439726308695933]
# [2018-06-15 04:56:50.288546] ridge_lgb mean cv score : 0.21416169818110148
# [2018-06-15 04:56:50.288657] ridge_lgb std cv score : 0.00037126033291255727

# [100]   training's rmse: 0.216434       valid_1's rmse: 0.220314
# [200]   training's rmse: 0.211524       valid_1's rmse: 0.217921
# [300]   training's rmse: 0.208081       valid_1's rmse: 0.216841
# [400]   training's rmse: 0.205299       valid_1's rmse: 0.216238
# [500]   training's rmse: 0.202826       valid_1's rmse: 0.215794
# [600]   training's rmse: 0.200479       valid_1's rmse: 0.215467
# [700]   training's rmse: 0.198461       valid_1's rmse: 0.215229
# [800]   training's rmse: 0.196764       valid_1's rmse: 0.215094
# [900]   training's rmse: 0.194996       valid_1's rmse: 0.214963
# [1000]  training's rmse: 0.19341        valid_1's rmse: 0.214862
# [1100]  training's rmse: 0.191906       valid_1's rmse: 0.214778
# [1200]  training's rmse: 0.19045        valid_1's rmse: 0.214724
# [1300]  training's rmse: 0.188933       valid_1's rmse: 0.214655
# [1400]  training's rmse: 0.18751        valid_1's rmse: 0.214616
# [1500]  training's rmse: 0.186169       valid_1's rmse: 0.21457
# [1600]  training's rmse: 0.18484        valid_1's rmse: 0.214545
# [1700]  training's rmse: 0.183561       valid_1's rmse: 0.214524
# [1800]  training's rmse: 0.182362       valid_1's rmse: 0.2145
# [1900]  training's rmse: 0.18113        valid_1's rmse: 0.214482
# [2000]  training's rmse: 0.179985       valid_1's rmse: 0.214468
# [2100]  training's rmse: 0.178885       valid_1's rmse: 0.214449
# [2200]  training's rmse: 0.177796       valid_1's rmse: 0.214436
# [2300]  training's rmse: 0.17673        valid_1's rmse: 0.214425
# [2400]  training's rmse: 0.175687       valid_1's rmse: 0.214415
# [2500]  training's rmse: 0.174676       valid_1's rmse: 0.214405
# [2600]  training's rmse: 0.173704       valid_1's rmse: 0.214401
# [2700]  training's rmse: 0.172746       valid_1's rmse: 0.214398
# [2800]  training's rmse: 0.171825       valid_1's rmse: 0.214397
# [2900]  training's rmse: 0.170892       valid_1's rmse: 0.214399
# [3000]  training's rmse: 0.169976       valid_1's rmse: 0.214396
# [3100]  training's rmse: 0.1691 valid_1's rmse: 0.214388