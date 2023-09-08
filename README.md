# VCSPM
一个使用简单的C/C++源码包管理器。

## 功能
- 支持本地包、远程包、远程源码文件、远程压缩包、git仓库、hg仓库、svn仓库等
- 包代码位于项目目录中，可以轻松访问
- 能够指定包的任何 git 标签、提交或分支
- 可筛选所需的文件
- 下载的包将缓存到用户目录，避免再次下载

## 要求
- Python >= 3.6
- Git >= 2.27
- Hg
- Svn
- patch

> 需要将以上程序路径添加到Path环境变量中

## 用法
有关完整示例，请参阅[示例](./example/)。

在项目目录中创建一个vcspm.json文件，并在字段中添加所需的包packages作为对象: 
```json
{
    "packages": {
        "package": {
            "version": "1.0.0",
            "type": "local",
            "path": "D:/package-1.0.0",
            "include": [],
            "exclude": []
        }
    }
}
```
命令行执行vcspm即可。

### 指定包仓库地址
包仓库用于存储预定义的包信息及补丁文件。

路径格式为`包仓库地址/包名首字母小写/包名/版本号/`

`vcspm.json`为包信息描述文件。

`patch.zip`为补丁或脚本文件，将自动解压到`vcspm/patchs/包名/`文件夹中。

```json
{
    "service_url": "包仓库地址url",
    "packages": {
        
    }
}
```

### 指定包安装目录
```json
{
    "install_dir": "vcspm/packages",
    "packages": {
        
    }
}
```

### 本地包
当指定`path`时将忽略`url`。

```json
{
    "packages": {
        "pkg_name": {            
            "version": "版本号",
            "type": "local",
            "url": "本地包路径",
            "path": "本地包路径"
        }
    }
}
```

### 远程仓库包
只需指定版本号，其余信息自动从`service_url`地址中获取。

```json
{
    "packages": {
        "pkg_name": "版本号"
    }
}
```

### 远程源码文件
`hash_type`可以为`SHA1`、`SHA256`。
```json
{
    "packages": {
        "pkg_name": {        
            "version": "版本号",
            "type": "sourcefile",
            "url": "源文件url",
            "hash_type": "hash类型",
            "file_hash": "文件指纹"
        }
    }
}
```

### 远程源码压缩包
`url`中可使用${version}指代版本号。
`url`可以指定为列表，第一个链接下载失败后自动尝试第二个，以此类推。
`rm_top_dir`为true将移除压缩包中的顶层目录。

```json
{
    "packages": {
        "pkg_name": {    
            "version": "版本号",
            "type": "archive",
            "url": "压缩包url",
            "hash_type": "hash类型-SHA1-SHA256",
            "file_hash": "文件指纹",
            "rm_top_dir": "true"
        }
    }
}
```

### Git仓库
当指定`git`时将忽略`url`。
`revision`可以为提交、标签、分支。

```json
{
    "packages": {
        "pkg_name": {  
            "version": "版本号",
            "type": "git",
            "url": "git地址",
            "git": "git地址",
            "revision": "commit或者tag"
        }
    }
}
```


### 筛选文件
使用`include`和`exclude`筛选文件，有选择的将需要的文件复制到包安装目录。
当`include`和`exclude`存在相同文件时，排除相应文件。

支持Unix shell 风格的通配符，如下：

| 模式     | 含意                        |
| :------- | :-------------------------- |
| `*`      | 匹配所有                    |
| `?`      | 匹配任何单个字符            |
| `[seq]`  | 匹配 *seq* 中的任何字符     |
| `[!seq]` | 匹配任何不在 *seq* 中的字符 |

对于字面值匹配，请将原字符用方括号括起来。 例如，`'[?]'` 将匹配字符 `'?'`。


```json
{
    "packages": {
        "pkg_name": {  
            "include": [
                "包含的文件",
                ""
            ],
            "exclude": [
                "排除的文件",
                ""
            ]
        }
    }
}
```

## 命令行参数

| 长选项             |短选项| 描述       |
|-------------------|----|----------|
| --help            | -h | 输出帮助     |
| --service-url     | -s | 包仓库地址    |
| --list            | -l | 列出全部可用的包 |
| --require         |    | 获取指定的包   |
| --skip            |    | 跳过指定的包   |
| --clean           | -c | 获取之前清除指定的包 |
| --clean-all       | -C | 获取之前清除全部包 |
| --debug           |    | 输出调试信息   |
| --break-on-error  |    | 出现错误立即中断获取 |

## 