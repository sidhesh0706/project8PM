def calculate_order_total(subtotal, tax, discount):
    total = subtotal + tax
    total -= tax
    return total