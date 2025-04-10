```RuntimeWarning: invalid value encountered in scalar power
  annual_return = 0 if self.trade_day == 0 else (1 + self.ret_day).cumprod()[len(self.ret_day) - 1] ** (
  ```

这个报错是因为self.ret_day为负，但是该值的数据类型是一个pandas Series，报错是因为计算年化时采用了幂运算的方式，因为年化参数还参与了很多其它运算，公式不太了解不好修改，暂不处理。知道是因为亏完了就行。