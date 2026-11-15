"""Current provincial four-team principals, scraped from China Economic Net
(district.ce.cn) province leadership pages, 2026-11. Names are used only as
roster snapshots; exact appointment dates are marked as start_precision=snapshot.
"""

CURRENT_PRINCIPALS = {
    "110000": {
        "party": ("\u5c39\u529b", "http://district.ce.cn/zt/rwk/sf/bj/index.shtml"),
        "government": ("\u6bb7\u52c7", "http://district.ce.cn/zt/rwk/sf/bj/index.shtml"),
        "congress": ("\u674e\u79c0\u9886", "http://district.ce.cn/zt/rwk/sf/bj/srd/201302/28/t20130228_770903.shtml"),
        "cppcc": (None, "http://district.ce.cn/zt/rwk/sf/bj/zx/201302/26/t20130226_770905.shtml"),
    },
    "120000": {
        "party": ("\u9648\u654f\u5c14", "http://district.ce.cn/zt/rwk/sf/tj/index.shtml"),
        "government": ("\u5f20\u5de5", "http://district.ce.cn/zt/rwk/sf/tj/index.shtml"),
        "congress": ("\u55bb\u4e91\u6797", "http://district.ce.cn/zt/rwk/sf/tj/rd/201302/28/t20130228_770907.shtml"),
        "cppcc": ("\u738b\u5e38\u677e", "http://district.ce.cn/zt/rwk/sf/tj/zx/201302/26/t20130226_770909.shtml"),
    },
    "130000": {
        "party": ("\u7f57\u6587", "http://district.ce.cn/zt/rwk/sf/he/index.shtml"),
        "government": ("\u8d75\u8fb0\u6615", "http://district.ce.cn/zt/rwk/sf/he/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/he/rd/201302/28/t20130228_770850.shtml"),
        "cppcc": ("\u5f20\u56fd\u534e", "http://district.ce.cn/zt/rwk/sf/he/zx/201302/26/t20130226_770911.shtml"),
    },
    "140000": {
        "party": ("\u5510\u767b\u6770", "http://district.ce.cn/zt/rwk/sf/sx/index.shtml"),
        "government": ("\u5362\u4e1c\u4eae", "http://district.ce.cn/zt/rwk/sf/sx/index.shtml"),
        "congress": ("\u5510\u767b\u6770", "http://district.ce.cn/zt/rwk/sf/sx/rd/201302/28/t20130228_770913.shtml"),
        "cppcc": ("\u5f20\u6625\u6797", "http://district.ce.cn/zt/rwk/sf/sx/zx/201302/26/t20130226_770852.shtml"),
    },
    "150000": {
        "party": ("\u738b\u4f1f\u4e2d", "http://district.ce.cn/zt/rwk/sf/nm/index.shtml"),
        "government": ("\u5305\u94a2", "http://district.ce.cn/zt/rwk/sf/nm/index.shtml"),
        "congress": ("\u738b\u4f1f\u4e2d", "http://district.ce.cn/zt/rwk/sf/nm/rd/201302/28/t20130228_770854.shtml"),
        "cppcc": ("\u5f20\u5ef6\u6606", "http://district.ce.cn/zt/rwk/sf/nm/zx/201302/26/t20130226_770915.shtml"),
    },
    "210000": {
        "party": ("\u8bb8\u6606\u6797", "http://district.ce.cn/zt/rwk/sf/ln/index.shtml"),
        "government": ("\u738b\u65b0\u4f1f", "http://district.ce.cn/zt/rwk/sf/ln/index.shtml"),
        "congress": ("\u8bb8\u6606\u6797", "http://district.ce.cn/zt/rwk/sf/ln/rd/201302/28/t20130228_770917.shtml"),
        "cppcc": ("\u5468\u6ce2", "http://district.ce.cn/zt/rwk/sf/ln/zx/201302/26/t20130226_770856.shtml"),
    },
    "220000": {
        "party": ("\u9ec4\u5f3a", "http://district.ce.cn/zt/rwk/sf/jl/index.shtml"),
        "government": ("\u80e1\u7389\u4ead", "http://district.ce.cn/zt/rwk/sf/jl/index.shtml"),
        "congress": ("\u9ec4\u5f3a", "http://district.ce.cn/zt/rwk/sf/jl/rd/201302/28/t20130228_770919.shtml"),
        "cppcc": ("\u6731\u56fd\u8d24", "http://district.ce.cn/zt/rwk/sf/jl/zx/201302/26/t20130226_770858.shtml"),
    },
    "230000": {
        "party": ("\u8bb8\u52e4", "http://district.ce.cn/zt/rwk/sf/hlj/index.shtml"),
        "government": ("\u6881\u60e0\u73b2", "http://district.ce.cn/zt/rwk/sf/hlj/index.shtml"),
        "congress": ("\u8bb8\u52e4", "http://district.ce.cn/zt/rwk/sf/hlj/rd/201302/28/t20130228_770921.shtml"),
        "cppcc": ("\u84dd\u7ecd\u654f", "http://district.ce.cn/zt/rwk/sf/hlj/zx/201302/26/t20130226_770860.shtml"),
    },
    "310000": {
        "party": ("\u9648\u5409\u5b81", "http://district.ce.cn/zt/rwk/sf/sh/index.shtml"),
        "government": ("\u6731\u5fe0\u660e", "http://district.ce.cn/zt/rwk/sf/sh/index.shtml"),
        "congress": ("\u9ec4\u8389\u65b0", "http://district.ce.cn/zt/rwk/sf/sh/rd/201303/04/t20130304_770924.shtml"),
        "cppcc": ("\u80e1\u6587\u5bb9", "http://district.ce.cn/zt/rwk/sf/sh/zx/201302/26/t20130226_770862.shtml"),
    },
    "320000": {
        "party": ("\u4fe1\u957f\u661f", "http://district.ce.cn/zt/rwk/sf/js/index.shtml"),
        "government": ("\u5218\u5c0f\u6d9b", "http://district.ce.cn/zt/rwk/sf/js/index.shtml"),
        "congress": ("\u4fe1\u957f\u661f", "http://district.ce.cn/zt/rwk/sf/js/rd/201303/04/t20130304_770926.shtml"),
        "cppcc": ("\u5f20\u4e49\u73cd", "http://district.ce.cn/zt/rwk/sf/js/zx/201302/26/t20130226_770864.shtml"),
    },
    "330000": {
        "party": ("\u738b\u6d69", "http://district.ce.cn/zt/rwk/sf/zj/index.shtml"),
        "government": ("\u5218\u6377", "http://district.ce.cn/zt/rwk/sf/zj/index.shtml"),
        "congress": ("\u738b\u6d69", "http://district.ce.cn/zt/rwk/sf/zj/rd/201303/04/t20130304_770867.shtml"),
        "cppcc": ("\u5ec9\u6bc5\u654f", "http://district.ce.cn/zt/rwk/sf/zj/zx/201302/26/t20130226_771006.shtml"),
    },
    "340000": {
        "party": ("\u674e\u4e50\u6210", "http://district.ce.cn/zt/rwk/sf/ah/index.shtml"),
        "government": ("\u738b\u4e1c\u4f1f", "http://district.ce.cn/zt/rwk/sf/ah/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/ah/rd/201303/04/t20130304_770927.shtml"),
        "cppcc": ("\u5f20\u897f\u660e", "http://district.ce.cn/zt/rwk/sf/ah/zx/201302/26/t20130226_771008.shtml"),
    },
    "350000": {
        "party": ("\u8d75\u9f99", "http://district.ce.cn/zt/rwk/sf/fj/index.shtml"),
        "government": ("\u90ed\u5b81\u5b81", "http://district.ce.cn/zt/rwk/sf/fj/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/fj/rd/201303/06/t20130306_771010.shtml"),
        "cppcc": ("\u6ed5\u4f73\u6750", "http://district.ce.cn/zt/rwk/sf/fj/zx/201302/26/t20130226_770929.shtml"),
    },
    "360000": {
        "party": ("\u5c39\u5f18", "http://district.ce.cn/zt/rwk/sf/jx/index.shtml"),
        "government": ("\u9648\u6c38\u5947", "http://district.ce.cn/zt/rwk/sf/jx/index.shtml"),
        "congress": ("\u5c39\u5f18", "http://district.ce.cn/zt/rwk/sf/jx/rd/201303/06/t20130306_770931.shtml"),
        "cppcc": ("\u5b8b\u798f\u9f99", "http://district.ce.cn/zt/rwk/sf/jx/zx/201302/26/t20130226_771014.shtml"),
    },
    "370000": {
        "party": ("\u6797\u6b66", "http://district.ce.cn/zt/rwk/sf/sd/index.shtml"),
        "government": ("\u5468\u4e43\u7fd4", "http://district.ce.cn/zt/rwk/sf/sd/index.shtml"),
        "congress": ("\u6797\u6b66", "http://district.ce.cn/zt/rwk/sf/sd/rd/201303/05/t20130305_770940.shtml"),
        "cppcc": ("\u845b\u6167\u541b", "http://district.ce.cn/zt/rwk/sf/sd/zx/201302/26/t20130226_770945.shtml"),
    },
    "410000": {
        "party": ("\u5468\u7956\u7ffc", "http://district.ce.cn/zt/rwk/sf/ha/index.shtml"),
        "government": ("\u738b\u9646\u8fdb", "http://district.ce.cn/zt/rwk/sf/ha/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/ha/rd/201303/06/t20130306_770947.shtml"),
        "cppcc": ("\u5b54\u660c\u751f", "http://district.ce.cn/zt/rwk/sf/ha/zx/201302/26/t20130226_771016.shtml"),
    },
    "420000": {
        "party": ("\u5173\u5fd7\u9e25", "http://district.ce.cn/zt/rwk/sf/hb/index.shtml"),
        "government": ("\u674e\u6bbf\u52cb", "http://district.ce.cn/zt/rwk/sf/hb/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/hb/rd/201303/05/t20130305_770954.shtml"),
        "cppcc": ("\u5b59\u4f1f", "http://district.ce.cn/zt/rwk/sf/hb/zx/201302/26/t20130226_770963.shtml"),
    },
    "430000": {
        "party": ("\u738b\u5fd7\u519b", "http://district.ce.cn/zt/rwk/sf/hn/index.shtml"),
        "government": ("\u8c22\u536b\u6c5f", "http://district.ce.cn/zt/rwk/sf/hn/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/hn/rd/201303/04/t20130304_771026.shtml"),
        "cppcc": ("\u6bdb\u4e07\u6625", "http://district.ce.cn/zt/rwk/sf/hn/zx/201302/26/t20130226_770965.shtml"),
    },
    "440000": {
        "party": ("\u9ec4\u5764\u660e", "http://district.ce.cn/zt/rwk/sf/gd/index.shtml"),
        "government": ("\u5b5f\u51e1\u5229", "http://district.ce.cn/zt/rwk/sf/gd/index.shtml"),
        "congress": ("\u9ec4\u695a\u5e73", "http://district.ce.cn/zt/rwk/sf/gd/rd/201303/04/t20130304_770967.shtml"),
        "cppcc": ("\u6797\u514b\u5e86", "http://district.ce.cn/zt/rwk/sf/gd/zx/201302/26/t20130226_770969.shtml"),
    },
    "450000": {
        "party": ("\u9648\u521a", "http://district.ce.cn/zt/rwk/sf/gx/index.shtml"),
        "government": ("\u97e6\u97ec", "http://district.ce.cn/zt/rwk/sf/gx/index.shtml"),
        "congress": ("\u9648\u521a", "http://district.ce.cn/zt/rwk/sf/gx/rd/201303/04/t20130304_771028.shtml"),
        "cppcc": ("\u5b59\u5927\u4f1f", "http://district.ce.cn/zt/rwk/sf/gx/xz/201302/26/t20130226_770971.shtml"),
    },
    "460000": {
        "party": ("\u51af\u98de", "http://district.ce.cn/zt/rwk/sf/hi/index.shtml"),
        "government": ("\u5218\u5c0f\u660e", "http://district.ce.cn/zt/rwk/sf/hi/index.shtml"),
        "congress": ("\u51af\u98de", "http://district.ce.cn/zt/rwk/sf/hi/rd/201303/04/t20130304_770973.shtml"),
        "cppcc": ("\u674e\u8363\u707f", "http://district.ce.cn/zt/rwk/sf/hi/zx/201302/26/t20130226_771030.shtml"),
    },
    "500000": {
        "party": ("\u8881\u5bb6\u519b", "http://district.ce.cn/zt/rwk/sf/cq/index.shtml"),
        "government": ("\u9648\u65b0\u6b66", "http://district.ce.cn/zt/rwk/sf/cq/index.shtml"),
        "congress": ("\u738b\u70af", "http://district.ce.cn/zt/rwk/sf/cq/rd/201303/04/t20130304_771032.shtml"),
        "cppcc": ("\u7a0b\u4e3d\u534e", "http://district.ce.cn/zt/rwk/sf/cq/zx/201302/26/t20130226_771034.shtml"),
    },
    "510000": {
        "party": ("\u738b\u6653\u6656", "http://district.ce.cn/zt/rwk/sf/sc/index.shtml"),
        "government": ("\u65bd\u5c0f\u7433", "http://district.ce.cn/zt/rwk/sf/sc/index.shtml"),
        "congress": ("\u738b\u6653\u6656", "http://district.ce.cn/zt/rwk/sf/sc/rd/201303/04/t20130304_770975.shtml"),
        "cppcc": ("\u7530\u5411\u5229", "http://district.ce.cn/zt/rwk/sf/sc/zx/201302/26/t20130226_770977.shtml"),
    },
    "520000": {
        "party": ("\u5f90\u9e9f", "http://district.ce.cn/zt/rwk/sf/gz/index.shtml"),
        "government": ("\u674e\u70b3\u519b", "http://district.ce.cn/zt/rwk/sf/gz/index.shtml"),
        "congress": ("\u5f90\u9e9f", "http://district.ce.cn/zt/rwk/sf/gz/rd/201303/04/t20130304_770979.shtml"),
        "cppcc": ("\u8d75\u6c38\u6e05", "http://district.ce.cn/zt/rwk/sf/gz/zx/201302/26/t20130226_771036.shtml"),
    },
    "530000": {
        "party": ("\u83ab\u9ad8\u4e49", "http://district.ce.cn/zt/rwk/sf/yn/index.shtml"),
        "government": ("\u5218\u5947\u51e1", "http://district.ce.cn/zt/rwk/sf/yn/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/yn/rd/201303/04/t20130304_770981.shtml"),
        "cppcc": ("\u5218\u6653\u51ef", "http://district.ce.cn/zt/rwk/sf/yn/zx/201302/26/t20130226_771038.shtml"),
    },
    "540000": {
        "party": ("\u80e1\u660c\u5347", "http://district.ce.cn/zt/rwk/sf/xz/index.shtml"),
        "government": ("\u560e\u739b\u6cfd\u767b", "http://district.ce.cn/zt/rwk/sf/xz/index.shtml"),
        "congress": ("\u4e25\u91d1\u6d77", "http://district.ce.cn/zt/rwk/sf/xz/rd/201303/04/t20130304_770983.shtml"),
        "cppcc": ("\u5e15\u5df4\u62c9\u00b7\u683c\u5217\u6717\u6770", "http://district.ce.cn/zt/rwk/sf/xz/zx/201302/26/t20130226_771040.shtml"),
    },
    "610000": {
        "party": ("\u8d75\u4e00\u5fb7", "http://district.ce.cn/zt/rwk/sf/sn/index.shtml"),
        "government": ("\u8d75\u521a", "http://district.ce.cn/zt/rwk/sf/sn/index.shtml"),
        "congress": ("\u8d75\u4e00\u5fb7", "http://district.ce.cn/zt/rwk/sf/sn/rd/201303/04/t20130304_770891.shtml"),
        "cppcc": ("\u5f90\u65b0\u8363", "http://district.ce.cn/zt/rwk/sf/sn/zx/201302/26/t20130226_770788.shtml"),
    },
    "620000": {
        "party": ("\u5434\u6653\u519b", "http://district.ce.cn/zt/rwk/sf/gs/index.shtml"),
        "government": ("\u5b54\u7ecd\u900a", "http://district.ce.cn/zt/rwk/sf/gs/index.shtml"),
        "congress": ("\u5434\u6653\u519b", "http://district.ce.cn/zt/rwk/sf/gs/rd/201303/05/t20130305_770986.shtml"),
        "cppcc": ("\u5e84\u56fd\u6cf0", "http://district.ce.cn/zt/rwk/sf/gs/zx/201302/26/t20130226_770987.shtml"),
    },
    "630000": {
        "party": ("\u7f57\u4e1c\u5ddd", "http://district.ce.cn/zt/rwk/sf/qh/index.shtml"),
        "government": ("\u8bf8\u845b\u5b87\u6770", "http://district.ce.cn/zt/rwk/sf/qh/index.shtml"),
        "congress": (None, "http://district.ce.cn/zt/rwk/sf/qh/rd/201303/08/t20130308_770989.shtml"),
        "cppcc": ("\u516c\u4fdd\u624e\u897f", "http://district.ce.cn/zt/rwk/sf/qh/zx/201302/26/t20130226_771042.shtml"),
    },
    "640000": {
        "party": ("\u674e\u9091\u98de", "http://district.ce.cn/zt/rwk/sf/nx/index.shtml"),
        "government": ("\u5f20\u96e8\u6d66", "http://district.ce.cn/zt/rwk/sf/nx/index.shtml"),
        "congress": ("\u674e\u9091\u98de", "http://district.ce.cn/zt/rwk/sf/nx/rd/201303/19/t20130319_771048.shtml"),
        "cppcc": ("\u9648\u96cd", "http://district.ce.cn/zt/rwk/sf/nx/zx/201302/26/t20130226_770998.shtml"),
    },
    "650000": {
        "party": ("\u9648\u5c0f\u6c5f", "http://district.ce.cn/zt/rwk/sf/xj/index.shtml"),
        "government": ("\u827e\u5c14\u80af\u00b7\u5410\u5c3c\u4e9a\u5b5c", "http://district.ce.cn/zt/rwk/sf/xj/index.shtml"),
        "congress": ("\u7956\u6728\u70ed\u63d0\u00b7\u543e\u5e03\u529b", "http://district.ce.cn/zt/rwk/sf/xj/rd/201303/05/t20130305_771052.shtml"),
        "cppcc": ("\u52aa\u5c14\u5170\u00b7\u963f\u4e0d\u90fd\u6ee1\u91d1", "http://district.ce.cn/zt/rwk/sf/xj/zx/201302/26/t20130226_771053.shtml"),
    },
}
