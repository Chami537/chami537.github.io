
# 1.两数之和

思路 用[[哈希表]]快速判断某个数字是否之前出现过

遍历每个数字:
    先检查数字或需要的数字是否已经存在
    如果存在，返回答案
    如果不存在，把当前数字保存进哈希表

利用查找key的方式从而把时间复杂度降到

$$
O(n)
$$

字典保存 

$$
数字 -> 下标
$$

判断是否存在某个key 平均复杂度为O(1)
```python
if num in hashmap:
```
判断是否存在某个value 平均复杂度为O(n)
```python
value in hashmap.values()
```

```python
class Solution(object):

    def twoSum(self, nums, target):

        hashmap={}

        for i,num in enumerate(nums):

            complement = target - num

            if complement in hashmap:

                return [hashmap[complement],i]

            hashmap[num]=i
```

# 2.存在重复元素

思路类似 直接上代码

```python
class Solution(object):

    def containsDuplicate(self, nums):

        """

        :type nums: List[int]

        :rtype: bool

        """

        hashmap={}

        for i,num in enumerate(nums):

            if num in hashmap:

                return True

            hashmap[num]=i

        return False
```