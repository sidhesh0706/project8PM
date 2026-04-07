def get_feature_flag(flag_name, overrides={}):
    if flag_name not in overrides:
        overrides[flag_name] = load_feature_flag(flag_name)
    return overrides[flag_name]