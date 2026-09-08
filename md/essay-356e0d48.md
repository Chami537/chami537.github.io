# 3. 无重复字符的最长子串

题目描述

给定一个字符串 `s` ，请你找出其中不含有重复字符的 **最长 子串** 的长度。

**示例 1:**

**输入:** s = "abcabcbb"
**输出:** 3 
**解释:** 因为无重复字符的最长子串是 `"abc"`，所以其长度为 3。注意 "bca" 和 "cab" 也是正确答案。

**示例 2:**

**输入:** s = "bbbbb"
**输出:** 1
**解释:** 因为无重复字符的最长子串是 `"b"`，所以其长度为 1。

**示例 3:**

**输入:** s = "pwwkew"
**输出:** 3
**解释:** 因为无重复字符的最长子串是 `"wke"`，所以其长度为 3。
请注意，你的答案必须是 **子串** 的长度，`"pwke"` 是一个子序列，不是子串。

## 第一版思路

从首字母开始用[[哈希表]]记录每个字母的出现次数 出现第二次就结束并返回字典长度

然后从1，2，i，n扫描原字符串即可

每次更新最大值

注：

>s[i:]表示从i开始的字符串

代码:

```python
class Solution(object):

    def lengthOfLongestSubstring(self, s):

        maxsize=0

        def returnstringlength(s):

            hashmap={}

            for c in s:

                if c in hashmap:

                    return len(hashmap)

                hashmap[c]=1

            return len(hashmap)

        for i in range(len(s)):

            maxsize = max(returnstringlength(s[i:]), maxsize)

        return maxsize
```


## 第二版思路


想象为一个队列 左右两指针维护左右两侧 

右指针向右移动 然后遇到现有窗口里的元素让左指针

**一格一格右移** 直到窗口中不再有重复字符

直到右指针指到队列末端 取这个过程的最大值

具体计数方式还是哈希表 

用hashmap[s[left]]判断窗口中是否有字符

注:

使用del来删除字典中的键

代码：

```python
class Solution(object):

    def lengthOfLongestSubstring(self, s):

        left=0

        right=0

        maxsize=0

        hashmap={}

        while right<len(s):

            if s[right] in hashmap:

                del hashmap[s[left]] #使用del来删除字典中的键

                left+=1

                continue

            hashmap[s[right]]=1

            right+=1

            maxsize=max(right-left,maxsize)

        return maxsize
```
## 时间复杂度

第一版：O(n²)
因为每个起点都可能重新向后扫描一遍。

第二版：O(n)
left 和 right 都只会从左往右移动，每个字符最多被加入和删除一次。

其中 continue 是一个比较巧妙的点 确保了左指针一定能移动到新的元素上去