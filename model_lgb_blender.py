import gc

from pprint import pprint

import pandas as pd
import numpy as np

import pathos.multiprocessing as mp

from sklearn.decomposition import TruncatedSVD

import lightgbm as lgb

from cv import run_cv_model
from utils import print_step, rmse
from cache import get_data, is_in_cache, load_cache, save_in_cache

params = {'learning_rate': 0.02,
          'application': 'regression',
          'num_leaves': 31,
          'verbosity': -1,
          'metric': 'rmse',
          'data_random_seed': 3,
          'bagging_fraction': 0.8,
          'feature_fraction': 0.8,
          'nthread': 16, #max(mp.cpu_count() - 2, 2),
          'lambda_l1': 1,
          'lambda_l2': 1,
          'min_data_in_leaf': 40,
          'num_rounds': 800, # 420
          'verbose_eval': 20}

def runLGB(train_X, train_y, test_X, test_y, test_X2, params):
    print_step('Prep LGB')
    d_train = lgb.Dataset(train_X, label=train_y)
    d_valid = lgb.Dataset(test_X, label=test_y)
    watchlist = [d_train, d_valid]
    print_step('Train LGB')
    num_rounds = params.pop('num_rounds')
    verbose_eval = params.pop('verbose_eval')
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
print_step('Importing Data 1/15')
train, test = get_data()

print('~~~~~~~~~~~~~~~')
print_step('Subsetting')
target = train['deal_probability']
train_id = train['item_id']
test_id = test['item_id']
train.drop(['deal_probability', 'item_id'], axis=1, inplace=True)
test.drop(['item_id'], axis=1, inplace=True)

print('~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Importing Data 2/15')
train_fe, test_fe = load_cache('data_with_fe')

print_step('Importing Data 2/15')
train_ridge, test_ridge = load_cache('tfidf_ridges')
drops = [c for c in train_ridge.columns if 'svd' in c or 'tfidf' in c]
train_ridge.drop(drops, axis=1, inplace=True)
test_ridge.drop(drops, axis=1, inplace=True)
train_ = train_ridge
test_ = test_ridge

print_step('Importing Data 2/15')
train_['parent_category_name'] = train_fe['parent_category_name']
test_['parent_category_name'] = test_fe['parent_category_name']
train_['price'] = train_fe['price']
test_['price'] = test_fe['price']

print_step('Importing Data 3/15 1/3')
train_base_lgb, test_base_lgb = load_cache('base_lgb')
print_step('Importing Data 3/15 2/3')
train_['base_lgb'] = train_base_lgb['base_lgb']
print_step('Importing Data 3/15 3/3')
test_['base_lgb'] = test_base_lgb['base_lgb']

print_step('Importing Data 3/15 1/3')
train_te_lgb, test_te_lgb = load_cache('te_lgb')
print_step('Importing Data 3/15 2/3')
train_['te_lgb'] = train_te_lgb['te_lgb']
print_step('Importing Data 3/15 3/3')
test_['te_lgb'] = test_te_lgb['te_lgb']

print_step('Importing Data 3/15 1/3')
train_ryan_lgbm_v29, test_ryan_lgbm_v29 = load_cache('ryan_lgbm_v29')
print_step('Importing Data 3/15 2/3')
train_['ryan_lgbm_v29'] = train_ryan_lgbm_v29['oof_lgbm']
print_step('Importing Data 3/15 3/3')
test_['ryan_lgbm_v29'] = test_ryan_lgbm_v29['oof_lgbm']

print_step('Importing Data 3/15 1/3')
train_ridge_lgb, test_ridge_lgb = load_cache('ridge_lgb')
print_step('Importing Data 3/15 2/3')
train_['ridge_lgb'] = train_ridge_lgb['ridge_lgb']
print_step('Importing Data 3/15 3/3')
test_['ridge_lgb'] = test_ridge_lgb['ridge_lgb']

print_step('Importing Data 4/15 1/4')
train_pcat_ridge, test_pcat_ridge = load_cache('parent_cat_ridges')
print_step('Importing Data 4/15 2/4')
train_pcat_ridge = train_pcat_ridge[[c for c in train_pcat_ridge.columns if 'ridge' in c]]
test_pcat_ridge = test_pcat_ridge[[c for c in test_pcat_ridge.columns if 'ridge' in c]]
print_step('Importing Data 4/15 3/4')
train_ = pd.concat([train_, train_pcat_ridge], axis=1)
print_step('Importing Data 4/15 4/4')
test_ = pd.concat([test_, test_pcat_ridge], axis=1)

print_step('Importing Data 5/15 1/4')
train_rcat_ridge, test_rcat_ridge = load_cache('parent_regioncat_ridges')
print_step('Importing Data 5/15 2/4')
train_rcat_ridge = train_rcat_ridge[[c for c in train_rcat_ridge.columns if 'ridge' in c]]
test_rcat_ridge = test_rcat_ridge[[c for c in test_rcat_ridge.columns if 'ridge' in c]]
print_step('Importing Data 5/15 3/4')
train_ = pd.concat([train_, train_rcat_ridge], axis=1)
print_step('Importing Data 5/15 4/4')
test_ = pd.concat([test_, test_rcat_ridge], axis=1)

print_step('Importing Data 6/15 1/4')
train_catb_ridge, test_catb_ridge = load_cache('cat_bin_ridges')
print_step('Importing Data 6/15 2/4')
train_catb_ridge = train_catb_ridge[[c for c in train_catb_ridge.columns if 'ridge' in c]]
test_catb_ridge = test_catb_ridge[[c for c in test_catb_ridge.columns if 'ridge' in c]]
print_step('Importing Data 6/15 3/4')
train_ = pd.concat([train_, train_catb_ridge], axis=1)
print_step('Importing Data 6/15 4/4')
test_ = pd.concat([test_, test_catb_ridge], axis=1)

print_step('Importing Data 7/15 1/3')
train_deep_lgb, test_deep_lgb = load_cache('deep_lgb')
print_step('Importing Data 7/15 2/3')
train_['deep_lgb'] = train_deep_lgb['deep_lgb']
print_step('Importing Data 7/15 3/3')
test_['deep_lgb'] = test_deep_lgb['deep_lgb']

print_step('Importing Data 8/15 1/3')
train_full_text_ridge, test_full_text_ridge = load_cache('full_text_ridge')
print_step('Importing Data 8/15 2/3')
train_['full_text_ridge'] = train_full_text_ridge['full_text_ridge']
print_step('Importing Data 8/15 3/3')
test_['full_text_ridge'] = test_full_text_ridge['full_text_ridge']

print_step('Importing Data 9/15 1/3')
train_complete_ridge, test_complete_ridge = load_cache('complete_ridge')
print_step('Importing Data 9/15 2/3')
train_['complete_ridge'] = train_complete_ridge['complete_ridge']
print_step('Importing Data 9/15 3/3')
test_['complete_ridge'] = test_complete_ridge['complete_ridge']

print_step('Importing Data 9/15 1/3')
train_ryan_ridge, test_ryan_ridge = load_cache('ryan_ridge_sgd_v2')
print_step('Importing Data 9/15 2/3')
train_['ryan_ridge'] = train_ryan_ridge['oof_ridge']
print_step('Importing Data 9/15 3/3')
test_['ryan_ridge'] = test_ryan_ridge['oof_ridge']
print_step('Importing Data 9/15 2/3')
train_['ryan_sgd'] = train_ryan_ridge['oof_sgd']
print_step('Importing Data 9/15 3/3')
test_['ryan_sgd'] = test_ryan_ridge['oof_sgd']

print_step('Importing Data 10/15 1/3')
train_complete_fm, test_complete_fm = load_cache('complete_fm')
print_step('Importing Data 10/15 2/3')
train_['complete_fm'] = train_complete_fm['complete_fm']
print_step('Importing Data 10/15 3/3')
test_['complete_fm'] = test_complete_fm['complete_fm']

print_step('Importing Data 11/15 1/3')
train_tffm2, test_tffm2 = load_cache('tffm2')
print_step('Importing Data 11/15 2/3')
train_['tffm2'] = train_tffm2['tffm2']
print_step('Importing Data 11/15 3/3')
test_['tffm2'] = test_tffm2['tffm2']

print_step('Importing Data 12/15 1/3')
train_tffm3, test_tffm3 = load_cache('tffm3')
print_step('Importing Data 12/15 2/3')
train_['tffm3'] = train_tffm3['tffm3']
print_step('Importing Data 12/15 3/3')
test_['tffm3'] = test_tffm3['tffm3']

print_step('Importing Data 13/15 1/3')
train_cnn_ft, test_cnn_ft = load_cache('CNN_FastText')
print_step('Importing Data 13/15 2/3')
train_['cnn_ft'] = train_cnn_ft['CNN_FastText']
print_step('Importing Data 13/15 3/3')
test_['cnn_ft'] = test_cnn_ft['CNN_FastText']

print_step('Importing Data 14/15 1/3')
train_cnn_ft, test_cnn_ft = load_cache('CNN_FastText_3')
print_step('Importing Data 14/15 2/3')
train_['cnn_ft3'] = train_cnn_ft['CNN_FastText_3']
print_step('Importing Data 14/15 3/3')
test_['cnn_ft3'] = test_cnn_ft['CNN_FastText_3']

print_step('Importing Data 14/15 1/3')
train_cnn_ft, test_cnn_ft = load_cache('CNN_FastText_4')
print_step('Importing Data 14/15 2/3')
train_['cnn_ft4'] = train_cnn_ft['CNN_FastText_4']
print_step('Importing Data 14/15 3/3')
test_['cnn_ft4'] = test_cnn_ft['CNN_FastText_4']

print_step('Importing Data 15/15 1/4')
train_img, test_img = load_cache('img_data')
cols = ['img_dullness_light_percent', 'img_dullness_dark_percent']
train_img = train_img[cols].fillna(0)
test_img = test_img[cols].fillna(0)
print_step('Importing Data 15/15 2/4')
train_fe = pd.concat([train_fe, train_img], axis=1)
print_step('Importing Data 15/15 3/4')
test_fe = pd.concat([test_fe, test_img], axis=1)
print_step('Importing Data 15/15 4/4')
train_['img_dullness_light_percent'] = train_fe['img_dullness_light_percent']
test_['img_dullness_light_percent'] = test_fe['img_dullness_light_percent']
train_['img_dullness_dark_percent'] = train_fe['img_dullness_dark_percent']
test_['img_dullness_dark_percent'] = test_fe['img_dullness_dark_percent']

print_step('Importing Data 15/15 4/4')
train_embeddings_df, test_embeddings_df = load_cache('avito_fasttext_300d')
print_step('Embedding SVD 1/4')
NCOMP = 20
svd = TruncatedSVD(n_components=NCOMP, algorithm='arpack')
svd.fit(train_embeddings_df)
print_step('Embedding SVD 2/4')
train_svd = pd.DataFrame(svd.transform(train_embeddings_df))
print_step('Embedding SVD 3/4')
test_svd = pd.DataFrame(svd.transform(test_embeddings_df))
print_step('Embedding SVD 4/4')
train_svd.columns = ['svd_embed_'+str(i+1) for i in range(NCOMP)]
test_svd.columns = ['svd_embed_'+str(i+1) for i in range(NCOMP)]
train_ = pd.concat([train_, train_svd], axis=1)
test_ = pd.concat([test_, test_svd], axis=1)

print('~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Converting to category')
cat_cols = ['region', 'city', 'parent_category_name', 'category_name', 'cat_bin',
            'param_1', 'param_2', 'param_3', 'user_type', 'image_top_1', 'day_of_week']
for col in train_.columns:
    print(col)
    if col in cat_cols:
        train_[col] = train_[col].astype('category')
        test_[col] = test_[col].astype('category')
    else:
        train_[col] = train_[col].astype(np.float64)
        test_[col] = test_[col].astype(np.float64)

print('~~~~~~~~~~~~')
print_step('Run LGB')
print(train_.shape)
print(test_.shape)
results = run_cv_model(train_, test_, target, runLGB, params, rmse, 'lgb_blender')
import pdb
pdb.set_trace()

print('~~~~~~~~~~')
print_step('Cache')
save_in_cache('lgb_blender', pd.DataFrame({'lgb_blender': results['train']}),
                             pd.DataFrame({'lgb_blender': results['test']}))

print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print_step('Prepping submission file')
submission = pd.DataFrame()
submission['item_id'] = test_id
submission['deal_probability'] = results['test'].clip(0.0, 1.0)
submission.to_csv('submit/submit_lgb_blender.csv', index=False)
print_step('Done!')

# [2018-06-18 16:16:54.438668] lgb_blender cv scores : [0.2120923791639136, 0.21127704177755158, 0.21127264952127392, 0.21108054813472305, 0.21163707986214958]
# [2018-06-18 16:16:54.438743] lgb_blender mean cv score : 0.21147193969192238
# [2018-06-18 16:16:54.438850] lgb_blender std cv score : 0.00035863784920655455

# [20]    training's rmse: 0.234902       valid_1's rmse: 0.235498
# [40]    training's rmse: 0.222572       valid_1's rmse: 0.223299
# [60]    training's rmse: 0.216685       valid_1's rmse: 0.217514
# [80]    training's rmse: 0.213895       valid_1's rmse: 0.214787
# [100]   training's rmse: 0.212546       valid_1's rmse: 0.213499
# [120]   training's rmse: 0.211869       valid_1's rmse: 0.212878
# [140]   training's rmse: 0.211507       valid_1's rmse: 0.212565
# [160]   training's rmse: 0.211293       valid_1's rmse: 0.212401
# [180]   training's rmse: 0.211153       valid_1's rmse: 0.212309
# [200]   training's rmse: 0.211049       valid_1's rmse: 0.212254
# [220]   training's rmse: 0.210964       valid_1's rmse: 0.212216
# [240]   training's rmse: 0.210891       valid_1's rmse: 0.212194
# [260]   training's rmse: 0.210825       valid_1's rmse: 0.212179
# [280]   training's rmse: 0.210763       valid_1's rmse: 0.21217
# [300]   training's rmse: 0.210706       valid_1's rmse: 0.21216
# [320]   training's rmse: 0.210652       valid_1's rmse: 0.212153
# [340]   training's rmse: 0.210597       valid_1's rmse: 0.212148
# [360]   training's rmse: 0.210545       valid_1's rmse: 0.212145
# [380]   training's rmse: 0.210493       valid_1's rmse: 0.212141
# [400]   training's rmse: 0.210448       valid_1's rmse: 0.212138
# [420]   training's rmse: 0.2104 valid_1's rmse: 0.212134
# [440]   training's rmse: 0.210353       valid_1's rmse: 0.212129
# [460]   training's rmse: 0.210306       valid_1's rmse: 0.212125
# [480]   training's rmse: 0.21026        valid_1's rmse: 0.212124
# [500]   training's rmse: 0.210215       valid_1's rmse: 0.212121
# [520]   training's rmse: 0.210171       valid_1's rmse: 0.212116
# [540]   training's rmse: 0.210127       valid_1's rmse: 0.212117
# [560]   training's rmse: 0.210082       valid_1's rmse: 0.212114
# [580]   training's rmse: 0.210037       valid_1's rmse: 0.212114
# [600]   training's rmse: 0.209992       valid_1's rmse: 0.212113
# [620]   training's rmse: 0.209947       valid_1's rmse: 0.212109
# [640]   training's rmse: 0.209904       valid_1's rmse: 0.212106
# [660]   training's rmse: 0.209858       valid_1's rmse: 0.212102
# [680]   training's rmse: 0.209814       valid_1's rmse: 0.212099
# [700]   training's rmse: 0.209769       valid_1's rmse: 0.212096
# [720]   training's rmse: 0.209727       valid_1's rmse: 0.212095
# [740]   training's rmse: 0.209683       valid_1's rmse: 0.212093
# [760]   training's rmse: 0.20964        valid_1's rmse: 0.212094
# [780]   training's rmse: 0.209597       valid_1's rmse: 0.212094
# [800]   training's rmse: 0.209555       valid_1's rmse: 0.212092
