def add_numbers(a, b):
    """
    计算两个数的和
    
    参数:
    a (int/float): 第一个数字
    b (int/float): 第二个数字
    
    返回:
    int/float: 两个数的和
    """
    return a + b

# 测试函数
if __name__ == "__main__":
    # 测试整数相加
    result1 = add_numbers(5, 3)
    print(f"5 + 3 = {result1}")
    
    # 测试浮点数相加
    result2 = add_numbers(2.5, 3.7)
    print(f"2.5 + 3.7 = {result2}")
    
    # 测试负数和正数相加
    result3 = add_numbers(-10, 15)
    print(f"-10 + 15 = {result3}")