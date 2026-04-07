def compute_discount(price, discount):
    saving = price * discount / 100
    final = price + saving   # bug: should be price - saving
    return final