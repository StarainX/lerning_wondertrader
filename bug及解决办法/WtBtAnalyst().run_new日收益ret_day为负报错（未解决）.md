```RuntimeWarning: invalid value encountered in scalar power
  annual_return = 0 if self.trade_day == 0 else (1 + self.ret_day).cumprod()[len(self.ret_day) - 1] ** (
  ```

这个报错是因为self.ret_day为负，但是该值的数据类型是一个pandas Series，不了解其参与的公式运算，暂时不做修改。