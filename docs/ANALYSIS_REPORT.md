# PB Project Analysis Report

**Generated:** 2026-04-14 15:19:29
**Source:** `exported`

## Summary

| Metric | Value |
|--------|-------|
| Source files | 156 |
| Objects | 156 |
| Total issues | 307 |
| Errors | 0 |
| Warnings | 54 |
| Info | 253 |

## Object Inventory

| Type | Count |
|------|-------|
| srw | 92 |

| srd | 49 |

| srf | 9 |

| srm | 3 |

| srj | 1 |

| srs | 1 |

| sru | 1 |

## Quality Issues

- [I] **m_btgl_main.srm** - Global variable 'm_btgl_main' (m_btgl_main)
- [I] **m_sngl_sygl.srm** - Global variable 'm_sngl_sygl' (m_sngl_sygl)
- [I] **m_zkgl_main.srm** - Global variable 'm_zkgl_main' (m_zkgl_main)
- [I] **n_cst_choosefont.sru** `choosefont` - 'choosefont' uses magic numbers: 88, 90, 120, 72, 400
- [I] **n_cst_choosefont.sru** `choosefont` - 'choosefont' lacks try-catch error handling
- [W] **n_cst_choosefont.sru** `choosefont` - 'choosefont' complexity=22 (rating=D, recommend <20)
- [I] **of_systemerror.srf** `of_systemerror` - 'of_systemerror' lacks try-catch error handling
- [W] **uf_get_fresh.srf** `uf_get_fresh` - 'uf_get_fresh' has hardcoded SQL - consider using DataWindow
- [I] **uf_get_fresh.srf** `uf_get_fresh` - 'uf_get_fresh' lacks try-catch error handling
- [I] **uf_get_roomtips.srf** `uf_get_roomtips` - 'uf_get_roomtips' lacks try-catch error handling
- [W] **uf_getmodarr.srf** `uf_getmodarr` - 'uf_getmodarr' has hardcoded SQL - consider using DataWindow
- [I] **uf_getmodarr.srf** `uf_getmodarr` - 'uf_getmodarr' lacks try-catch error handling
- [I] **uf_print_grid_ds.srf** `uf_print_grid_ds` - 'uf_print_grid_ds' uses magic numbers: 240, 12, 200
- [I] **uf_print_grid_ds.srf** `uf_print_grid_ds` - 'uf_print_grid_ds' lacks try-catch error handling
- [W] **uf_zf_hfqz.srf** `uf_zf_hfqz` - 'uf_zf_hfqz' has hardcoded SQL - consider using DataWindow
- [I] **uf_zf_hfqz.srf** `uf_zf_hfqz` - 'uf_zf_hfqz' lacks try-catch error handling
- [I] **uf_zf_openroom.srf** `uf_zf_openroom` - 'uf_zf_openroom' uses magic numbers: 12
- [W] **uf_zf_openroom.srf** `uf_zf_openroom` - 'uf_zf_openroom' has hardcoded SQL - consider using DataWindow
- [I] **uf_zf_openroom.srf** `uf_zf_openroom` - 'uf_zf_openroom' lacks try-catch error handling
- [I] **uf_zf_tip.srf** `uf_zf_tip` - 'uf_zf_tip' uses magic numbers: 24, 60
- [I] **uf_zf_tip.srf** `uf_zf_tip` - 'uf_zf_tip' lacks try-catch error handling
- [W] **uf_zf_zs.srf** `uf_zf_zs` - 'uf_zf_zs' has hardcoded SQL - consider using DataWindow
- [I] **uf_zf_zs.srf** `uf_zf_zs` - 'uf_zf_zs' lacks try-catch error handling
- [I] **w_js_base.srw** `SetActiveWindow` - 'SetActiveWindow' lacks try-catch error handling
- [I] **w_js_base.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_js_base.srw** - Global variable 'w_js_base' (w_js_base)
- [I] **w_list_jszs.srw** - Global variable 'w_list_jszs' (w_list_jszs)
- [I] **w_list_jszs_history.srw** - Global variable 'w_list_jszs_history' (w_list_jszs_history)
- [I] **w_list_jszs_tj.srw** - Global variable 'w_list_jszs_tj' (w_list_jszs_tj)
- [I] **w_list_jszs_tj_history.srw** - Global variable 'w_list_jszs_tj_history' (w_list_jszs_tj_history)
- [I] **w_list_kstj.srw** `mousemove` - 'mousemove' uses magic numbers: 46, 176, 3662, 1584, 20
- [I] **w_list_kstj.srw** - Global variable 'w_list_kstj' (w_list_kstj)
- [I] **w_list_kstj_history.srw** `mousemove` - 'mousemove' uses magic numbers: 46, 176, 3662, 1584, 20
- [I] **w_list_kstj_history.srw** - Global variable 'w_list_kstj_history' (w_list_kstj_history)
- [I] **w_list_missworks.srw** - Global variable 'w_list_missworks' (w_list_missworks)
- [I] **w_list_missworks_history.srw** - Global variable 'w_list_missworks_history' (w_list_missworks_history)
- [I] **w_list_orders.srw** - Global variable 'w_list_orders' (w_list_orders)
- [I] **w_list_orders_history.srw** - Global variable 'w_list_orders_history' (w_list_orders_history)
- [I] **w_list_srfx.srw** `mousemove` - 'mousemove' uses magic numbers: 38, 40
- [I] **w_list_srfx.srw** - Global variable 'w_list_srfx' (w_list_srfx)
- [I] **w_sngl_btgl.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sngl_btgl.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sngl_btgl.srw** `resize` - 'resize' uses magic numbers: 2665, 40, 1056, 1816, 30
- [I] **w_sngl_btgl.srw** `mousemove` - 'mousemove' uses magic numbers: 14, 2583, 1832, 20
- [I] **w_sngl_btgl_add.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [W] **w_sngl_btgl_add.srw** `wf_save` - 'wf_save' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_btgl_add.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [W] **w_sngl_btgl_add.srw** `wf_save` - 'wf_save' complexity=27 (rating=D, recommend <20)
- [I] **w_sngl_btgl_add.srw** `key` - 'key' uses magic numbers: 2149, 336, 1166, 996, 20
- [I] **w_sngl_btgl_add.srw** - Global variable 'w_sngl_btgl_add' (w_sngl_btgl_add)
- [I] **w_sngl_checkout_fwf.srw** - Global variable 'w_sngl_checkout_fwf' (w_sngl_checkout_fwf)
- [I] **w_sngl_checkout_getfh.srw** - Global variable 'w_sngl_checkout_getfh' (w_sngl_checkout_getfh)
- [I] **w_sngl_checkout_js.srw** - Global variable 'w_sngl_checkout_js' (w_sngl_checkout_js)
- [I] **w_sngl_checkout_pay3.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_checkout_pay3.srw** `wf_pay` - 'wf_pay' uses magic numbers: 3
- [I] **w_sngl_checkout_pay3.srw** `wf_pay` - 'wf_pay' lacks try-catch error handling
- [W] **w_sngl_checkout_pay3.srw** `of_getpayment` - 'of_getpayment' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_checkout_pay3.srw** `of_getpayment` - 'of_getpayment' lacks try-catch error handling
- [I] **w_sngl_checkout_pay3.srw** - Global variable 'w_sngl_checkout_pay3' (w_sngl_checkout_pay3)
- [I] **w_sngl_getcardid.srw** `wf_dec2hex` - 'wf_dec2hex' uses magic numbers: 15, 48, 49, 50, 51
- [I] **w_sngl_getcardid.srw** `wf_dec2hex` - 'wf_dec2hex' lacks try-catch error handling
- [I] **w_sngl_getcardid.srw** `wf_getwgm` - 'wf_getwgm' uses magic numbers: 6, 3
- [I] **w_sngl_getcardid.srw** `wf_getwgm` - 'wf_getwgm' lacks try-catch error handling
- [I] **w_sngl_getcardid.srw** `wf_hex2dec` - 'wf_hex2dec' uses magic numbers: 9
- [I] **w_sngl_getcardid.srw** `wf_hex2dec` - 'wf_hex2dec' lacks try-catch error handling
- [I] **w_sngl_getcardid.srw** `wf_key` - 'wf_key' uses magic numbers: 3, 5, 6, 7, 9
- [I] **w_sngl_getcardid.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_getcardid.srw** - Global variable 'w_sngl_getcardid' (w_sngl_getcardid)
- [I] **w_sngl_getfh.srw** - Global variable 'w_sngl_getfh' (w_sngl_getfh)
- [I] **w_sngl_getjs.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_getjs.srw** - Global variable 'w_sngl_getjs' (w_sngl_getjs)
- [I] **w_sngl_getjs_insert.srw** - Global variable 'w_sngl_getjs_insert' (w_sngl_getjs_insert)
- [I] **w_sngl_getzs.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_getzs.srw** - Global variable 'w_sngl_getzs' (w_sngl_getzs)
- [I] **w_sngl_group.srw** `wf_1to2` - 'wf_1to2' lacks try-catch error handling
- [I] **w_sngl_group.srw** `wf_2to1` - 'wf_2to1' lacks try-catch error handling
- [I] **w_sngl_group.srw** - Global variable 'w_sngl_group' (w_sngl_group)
- [I] **w_sngl_group_fc.srw** `wf_1to2` - 'wf_1to2' lacks try-catch error handling
- [I] **w_sngl_group_fc.srw** `wf_2to1` - 'wf_2to1' lacks try-catch error handling
- [I] **w_sngl_group_fc.srw** - Global variable 'w_sngl_group_fc' (w_sngl_group_fc)
- [I] **w_sngl_items_add.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [W] **w_sngl_items_add.srw** `wf_save` - 'wf_save' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_items_add.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sngl_items_add.srw** `wf_setfjbh` - 'wf_setfjbh' lacks try-catch error handling
- [I] **w_sngl_items_add.srw** `key` - 'key' uses magic numbers: 9, 132, 955, 804, 20
- [I] **w_sngl_items_add.srw** - Global variable 'w_sngl_items_add' (w_sngl_items_add)
- [I] **w_sngl_jb_opter.srw** - Global variable 'w_sngl_jb_opter' (w_sngl_jb_opter)
- [I] **w_sngl_js_add.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_add.srw** - Global variable 'w_sngl_js_add' (w_sngl_js_add)
- [I] **w_sngl_js_atten.srw** `key` - 'key' uses magic numbers: 2208, 888
- [I] **w_sngl_js_atten.srw** - Global variable 'w_sngl_js_atten' (w_sngl_js_atten)
- [I] **w_sngl_js_begin.srw** `wf_setfjbh` - 'wf_setfjbh' lacks try-catch error handling
- [I] **w_sngl_js_begin.srw** `wf_setjsbh` - 'wf_setjsbh' uses magic numbers: 3
- [I] **w_sngl_js_begin.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_begin.srw** - Global variable 'w_sngl_js_begin' (w_sngl_js_begin)
- [I] **w_sngl_js_div.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_div.srw** - Global variable 'w_sngl_js_div' (w_sngl_js_div)
- [I] **w_sngl_js_end.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_end.srw** - Global variable 'w_sngl_js_end' (w_sngl_js_end)
- [I] **w_sngl_js_groupid.srw** - Global variable 'w_sngl_js_groupid' (w_sngl_js_groupid)
- [I] **w_sngl_js_js.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_js.srw** - Global variable 'w_sngl_js_js' (w_sngl_js_js)
- [I] **w_sngl_js_mode.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sngl_js_mode.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_mode.srw** - Global variable 'w_sngl_js_mode' (w_sngl_js_mode)
- [I] **w_sngl_js_new.srw** `wf_setfjbh` - 'wf_setfjbh' lacks try-catch error handling
- [I] **w_sngl_js_new.srw** - Global variable 'w_sngl_js_new' (w_sngl_js_new)
- [I] **w_sngl_js_query.srw** - Global variable 'w_sngl_js_query' (w_sngl_js_query)
- [W] **w_sngl_js_res.srw** `of_getserver` - 'of_getserver' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_js_res.srw** `of_getserver` - 'of_getserver' lacks try-catch error handling
- [I] **w_sngl_js_res.srw** `keydown` - 'keydown' uses magic numbers: 640, 88, 1787, 764, 9
- [I] **w_sngl_js_res.srw** - Global variable 'w_sngl_js_res' (w_sngl_js_res)
- [I] **w_sngl_js_reslist.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_js_reslist.srw** `key` - 'key' uses magic numbers: 37, 132, 2075, 680
- [I] **w_sngl_js_reslist.srw** - Global variable 'w_sngl_js_reslist' (w_sngl_js_reslist)
- [W] **w_sngl_js_room.srw** `wf_jschangeroom` - 'wf_jschangeroom' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_js_room.srw** `wf_jschangeroom` - 'wf_jschangeroom' lacks try-catch error handling
- [W] **w_sngl_js_room.srw** `wf_roomchangeroom` - 'wf_roomchangeroom' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_js_room.srw** `wf_roomchangeroom` - 'wf_roomchangeroom' lacks try-catch error handling
- [I] **w_sngl_js_room.srw** `wf_setfjbh` - 'wf_setfjbh' lacks try-catch error handling
- [I] **w_sngl_js_room.srw** `wf_setjsbh` - 'wf_setjsbh' lacks try-catch error handling
- [I] **w_sngl_js_room.srw** - Global variable 'w_sngl_js_room' (w_sngl_js_room)
- [I] **w_sngl_js_rs.srw** - Global variable 'w_sngl_js_rs' (w_sngl_js_rs)
- [I] **w_sngl_js_status.srw** - Global variable 'w_sngl_js_status' (w_sngl_js_status)
- [I] **w_sngl_lmgl_rmst.srw** - Global variable 'w_sngl_lmgl_rmst' (w_sngl_lmgl_rmst)
- [I] **w_sngl_main.srw** `ue_rjcz` - 'ue_rjcz' uses magic numbers: 60
- [I] **w_sngl_main.srw** `of_clipcursor` - 'of_clipcursor' lacks try-catch error handling
- [W] **w_sngl_main.srw** `of_get_dw` - 'of_get_dw' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_main.srw** `of_get_dw` - 'of_get_dw' lacks try-catch error handling
- [W] **w_sngl_main.srw** `of_get_rpt` - 'of_get_rpt' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_main.srw** `of_get_rpt` - 'of_get_rpt' lacks try-catch error handling
- [W] **w_sngl_main.srw** `of_get_rpt2` - 'of_get_rpt2' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_main.srw** `of_get_rpt2` - 'of_get_rpt2' lacks try-catch error handling
- [W] **w_sngl_main.srw** `of_get_rpt2` - 'of_get_rpt2' complexity=22 (rating=D, recommend <20)
- [I] **w_sngl_main.srw** `wf_set_statusbar` - 'wf_set_statusbar' uses magic numbers: 150, 250, 200, 3, 5
- [I] **w_sngl_main.srw** `wf_set_statusbar` - 'wf_set_statusbar' lacks try-catch error handling
- [W] **w_sngl_main.srw** `wf_set_statusbar` - 'wf_set_statusbar' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sngl_main.srw** `wf_setmicrohelp` - 'wf_setmicrohelp' lacks try-catch error handling
- [I] **w_sngl_main.srw** `wf_setwindow` - 'wf_setwindow' uses magic numbers: 600, 800
- [I] **w_sngl_main.srw** `wf_setwindow` - 'wf_setwindow' lacks try-catch error handling
- [I] **w_sngl_main.srw** `wf_updatestatusbar` - 'wf_updatestatusbar' uses magic numbers: 3
- [I] **w_sngl_main.srw** `wf_updatestatusbar` - 'wf_updatestatusbar' lacks try-catch error handling
- [I] **w_sngl_main.srw** `destroy` - 'destroy' uses magic numbers: 224, 136, 30, 178, 1172
- [I] **w_sngl_payment.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_payment.srw** `key` - 'key' uses magic numbers: 37, 144, 850, 916
- [I] **w_sngl_payment.srw** - Global variable 'w_sngl_payment' (w_sngl_payment)
- [I] **w_sngl_res_call.srw** - Global variable 'w_sngl_res_call' (w_sngl_res_call)
- [I] **w_sngl_res_new.srw** - Global variable 'w_sngl_res_new' (w_sngl_res_new)
- [I] **w_sngl_rj_opter.srw** - Global variable 'w_sngl_rj_opter' (w_sngl_rj_opter)
- [W] **w_sngl_sygl.srw** `wf_getbillid` - 'wf_getbillid' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_sygl.srw** `wf_getbillid` - 'wf_getbillid' lacks try-catch error handling
- [I] **w_sngl_sygl.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_sygl.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [I] **w_sngl_sygl.srw** `wf_room_retrieve` - 'wf_room_retrieve' lacks try-catch error handling
- [W] **w_sngl_sygl.srw** `wf_room_tab` - 'wf_room_tab' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_sygl.srw** `wf_room_tab` - 'wf_room_tab' lacks try-catch error handling
- [I] **w_sngl_sygl.srw** `resize` - 'resize' uses magic numbers: 18, 3493, 780
- [I] **w_sngl_sygl.srw** `key` - 'key' uses magic numbers: 14, 2624, 684, 20
- [I] **w_sngl_sygl.srw** `key` - 'key' uses magic numbers: 2459, 716, 20
- [I] **w_sngl_sygl.srw** `key` - 'key' uses magic numbers: 50, 1020, 2341, 400, 20
- [I] **w_sngl_sygl_detail.srw** `wf_check_js_work` - 'wf_check_js_work' lacks try-catch error handling
- [I] **w_sngl_sygl_detail.srw** `wf_checkout_new` - 'wf_checkout_new' lacks try-catch error handling
- [W] **w_sngl_sygl_detail.srw** `wf_discount` - 'wf_discount' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_sygl_detail.srw** `wf_discount` - 'wf_discount' lacks try-catch error handling
- [I] **w_sngl_sygl_detail.srw** `wf_discount_new` - 'wf_discount_new' uses magic numbers: 13
- [W] **w_sngl_sygl_detail.srw** `wf_discount_new` - 'wf_discount_new' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_sygl_detail.srw** `wf_discount_new` - 'wf_discount_new' lacks try-catch error handling
- [W] **w_sngl_sygl_detail.srw** `wf_js_xz` - 'wf_js_xz' has hardcoded SQL - consider using DataWindow
- [I] **w_sngl_sygl_detail.srw** `wf_js_xz` - 'wf_js_xz' lacks try-catch error handling
- [I] **w_sngl_sygl_detail.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_sygl_detail.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sngl_sygl_detail.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sngl_sygl_detail.srw** `key` - 'key' uses magic numbers: 2066, 2104, 20
- [I] **w_sngl_sygl_detail.srw** - Global variable 'w_sngl_sygl_detail' (w_sngl_sygl_detail)
- [I] **w_sngl_zfgl.srw** `wf_key` - 'wf_key' lacks try-catch error handling
- [I] **w_sngl_zfgl.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sngl_zfgl.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sngl_zfgl.srw** `wf_sendfh` - 'wf_sendfh' lacks try-catch error handling
- [I] **w_sngl_zfgl.srw** `wf_setwin` - 'wf_setwin' uses magic numbers: 3, 5, 6, 7, 9
- [I] **w_sngl_zfgl.srw** `wf_setwin` - 'wf_setwin' lacks try-catch error handling
- [I] **w_sngl_zfgl.srw** `wf_sendjs` - 'wf_sendjs' lacks try-catch error handling
- [I] **w_sngl_zfgl.srw** `key` - 'key' uses magic numbers: 18, 1096, 1723, 580, 30
- [I] **w_sngl_zfgl.srw** `key` - 'key' uses magic numbers: 18, 1723, 1028
- [I] **w_sngl_zfgl.srw** `resize` - 'resize' uses magic numbers: 1824, 52, 1399, 1624, 30
- [I] **w_sngl_zfgl.srw** `key` - 'key' uses magic numbers: 82, 288, 1198, 1120, 50
- [I] **w_sngl_zfgl.srw** `key` - 'key' uses magic numbers: 46, 80, 1198, 1340, 50
- [I] **w_sngl_zfgl.srw** `create` - 'create' uses magic numbers: 18, 96, 1362, 1512, 69
- [I] **w_sngl_zkgl_rmst.srw** - Global variable 'w_sngl_zkgl_rmst' (w_sngl_zkgl_rmst)
- [I] **w_sys_about.srw** - Global variable 'w_sys_about' (w_sys_about)
- [I] **w_sys_accbills.srw** - Global variable 'w_sys_accbills' (w_sys_accbills)
- [I] **w_sys_accbills_audit_list.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sys_accbills_audit_list.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_accbills_audit_list.srw** - Global variable 'w_sys_accbills_audit_list' (w_sys_accbills_audit_list)
- [I] **w_sys_accbills_list.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sys_accbills_list.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_accbills_list.srw** - Global variable 'w_sys_accbills_list' (w_sys_accbills_list)
- [I] **w_sys_accitems.srw** - Global variable 'w_sys_accitems' (w_sys_accitems)
- [I] **w_sys_addtype.srw** - Global variable 'w_sys_addtype' (w_sys_addtype)
- [I] **w_sys_background.srw** `of_createdw` - 'of_createdw' lacks try-catch error handling
- [I] **w_sys_background.srw** `of_setbg` - 'of_setbg' uses magic numbers: 6
- [I] **w_sys_background.srw** `of_setbg` - 'of_setbg' lacks try-catch error handling
- [W] **w_sys_background.srw** `of_setbg` - 'of_setbg' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_background.srw** - Global variable 'w_sys_background' (w_sys_background)
- [I] **w_sys_bellsetting.srw** `of_execute` - 'of_execute' lacks try-catch error handling
- [W] **w_sys_bellsetting.srw** `of_execute` - 'of_execute' uses deprecated: SetPointer (use Pointer property)
- [I] **w_sys_bellsetting.srw** `of_execute` - 'of_execute' lacks try-catch error handling
- [W] **w_sys_bellsetting.srw** `of_execute` - 'of_execute' uses deprecated: SetPointer (use Pointer property)
- [I] **w_sys_bellsetting.srw** `of_notify` - 'of_notify' lacks try-catch error handling
- [W] **w_sys_bellsetting.srw** `of_notify` - 'of_notify' uses deprecated: SetPointer (use Pointer property)
- [I] **w_sys_bellsetting.srw** `of_uplaod` - 'of_uplaod' uses magic numbers: 11
- [I] **w_sys_bellsetting.srw** `of_uplaod` - 'of_uplaod' lacks try-catch error handling
- [I] **w_sys_bellsetting.srw** - Global variable 'w_sys_bellsetting' (w_sys_bellsetting)
- [I] **w_sys_busy.srw** - Global variable 'w_sys_busy' (w_sys_busy)
- [I] **w_sys_caller.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sys_caller.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_caller.srw** - Global variable 'w_sys_caller' (w_sys_caller)
- [I] **w_sys_changepas.srw** - Global variable 'w_sys_changepas' (w_sys_changepas)
- [I] **w_sys_connectinfo.srw** `GetModuleFileNameA` - 'GetModuleFileNameA' lacks try-catch error handling
- [I] **w_sys_connectinfo.srw** - Global variable 'w_sys_connectinfo' (w_sys_connectinfo)
- [W] **w_sys_data.srw** `wf_backup` - 'wf_backup' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_data.srw** `wf_backup` - 'wf_backup' lacks try-catch error handling
- [W] **w_sys_data.srw** `wf_backup` - 'wf_backup' uses deprecated: SetPointer (use Pointer property)
- [W] **w_sys_data.srw** `wf_bf` - 'wf_bf' has hardcoded SQL - consider using DataWindow
- [W] **w_sys_data.srw** `wf_bf` - 'wf_bf' uses deprecated: SetPointer (use Pointer property)
- [I] **w_sys_data.srw** `wf_export` - 'wf_export' lacks try-catch error handling
- [W] **w_sys_data.srw** `wf_hf` - 'wf_hf' has hardcoded SQL - consider using DataWindow
- [W] **w_sys_data.srw** `wf_hf` - 'wf_hf' uses deprecated: SetPointer (use Pointer property)
- [I] **w_sys_data.srw** `wf_import` - 'wf_import' lacks try-catch error handling
- [W] **w_sys_data.srw** `wf_restore` - 'wf_restore' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_data.srw** `wf_restore` - 'wf_restore' lacks try-catch error handling
- [W] **w_sys_data.srw** `wf_restore` - 'wf_restore' uses deprecated: SetPointer (use Pointer property)
- [I] **w_sys_data.srw** `of_export` - 'of_export' uses magic numbers: 3
- [W] **w_sys_data.srw** `of_export` - 'of_export' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_data.srw** `of_export` - 'of_export' lacks try-catch error handling
- [I] **w_sys_data.srw** `of_import` - 'of_import' uses magic numbers: 3
- [W] **w_sys_data.srw** `of_import` - 'of_import' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_data.srw** `of_import` - 'of_import' lacks try-catch error handling
- [I] **w_sys_data.srw** - Global variable 'w_sys_data' (w_sys_data)
- [W] **w_sys_employee_detail.srw** `wf_getphoto` - 'wf_getphoto' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_employee_detail.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [W] **w_sys_employee_detail.srw** `wf_save` - 'wf_save' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_employee_detail.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [W] **w_sys_employee_detail.srw** `wf_setphoto` - 'wf_setphoto' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_employee_detail.srw** `wf_setphoto` - 'wf_setphoto' lacks try-catch error handling
- [I] **w_sys_employee_detail.srw** - Global variable 'w_sys_employee_detail' (w_sys_employee_detail)
- [I] **w_sys_employee_list.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sys_employee_list.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_employee_list.srw** - Global variable 'w_sys_employee_list' (w_sys_employee_list)
- [I] **w_sys_employee_stype.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [W] **w_sys_employee_stype.srw** `wf_save` - 'wf_save' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_employee_stype.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_employee_stype.srw** - Global variable 'w_sys_employee_stype' (w_sys_employee_stype)
- [W] **w_sys_getrq.srw** `wf_getservice` - 'wf_getservice' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_getrq.srw** `wf_getservice` - 'wf_getservice' lacks try-catch error handling
- [I] **w_sys_getrq.srw** - Global variable 'w_sys_getrq' (w_sys_getrq)
- [I] **w_sys_getrq2.srw** - Global variable 'w_sys_getrq2' (w_sys_getrq2)
- [I] **w_sys_getrq3.srw** - Global variable 'w_sys_getrq3' (w_sys_getrq3)
- [W] **w_sys_getyf.srw** `wf_getservice` - 'wf_getservice' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_getyf.srw** `wf_getservice` - 'wf_getservice' lacks try-catch error handling
- [I] **w_sys_getyf.srw** - Global variable 'w_sys_getyf' (w_sys_getyf)
- [I] **w_sys_items_list.srw** - Global variable 'w_sys_items_list' (w_sys_items_list)
- [I] **w_sys_jsgz.srw** `of_getxm` - 'of_getxm' lacks try-catch error handling
- [I] **w_sys_jsgz.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sys_jsgz.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_jsgz.srw** - Global variable 'w_sys_jsgz' (w_sys_jsgz)
- [I] **w_sys_jsgz_list.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sys_jsgz_list.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_jsgz_list.srw** - Global variable 'w_sys_jsgz_list' (w_sys_jsgz_list)
- [I] **w_sys_log.srw** - Global variable 'w_sys_log' (w_sys_log)
- [I] **w_sys_login.srw** - Global variable 'w_sys_login' (w_sys_login)
- [W] **w_sys_missesold_detail.srw** `wf_getphoto` - 'wf_getphoto' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_missesold_detail.srw** - Global variable 'w_sys_missesold_detail' (w_sys_missesold_detail)
- [I] **w_sys_missitems_detail.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sys_missitems_detail.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_missitems_detail.srw** - Global variable 'w_sys_missitems_detail' (w_sys_missitems_detail)
- [I] **w_sys_missitems_list.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sys_missitems_list.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_missitems_list.srw** - Global variable 'w_sys_missitems_list' (w_sys_missitems_list)
- [I] **w_sys_missitemstype.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [W] **w_sys_missitemstype.srw** `wf_save` - 'wf_save' has hardcoded SQL - consider using DataWindow
- [I] **w_sys_missitemstype.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_missitemstype.srw** - Global variable 'w_sys_missitemstype' (w_sys_missitemstype)
- [I] **w_sys_payment.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sys_payment.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_payment.srw** - Global variable 'w_sys_payment' (w_sys_payment)
- [I] **w_sys_rooms_detail.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sys_rooms_detail.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_rooms_detail.srw** - Global variable 'w_sys_rooms_detail' (w_sys_rooms_detail)
- [I] **w_sys_rooms_list.srw** `wf_refresh` - 'wf_refresh' lacks try-catch error handling
- [W] **w_sys_rooms_list.srw** `wf_refresh` - 'wf_refresh' uses deprecated: SetRedraw (use SetRedraw property)
- [I] **w_sys_rooms_list.srw** - Global variable 'w_sys_rooms_list' (w_sys_rooms_list)
- [I] **w_sys_roomtype.srw** `wf_new` - 'wf_new' lacks try-catch error handling
- [I] **w_sys_roomtype.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_roomtype.srw** - Global variable 'w_sys_roomtype' (w_sys_roomtype)
- [I] **w_sys_roomtype_list.srw** - Global variable 'w_sys_roomtype_list' (w_sys_roomtype_list)
- [I] **w_sys_setbg.srw** `create` - 'create' uses magic numbers: 18, 104, 2267, 936, 197
- [I] **w_sys_setbg.srw** - Global variable 'w_sys_setbg' (w_sys_setbg)
- [I] **w_sys_splash.srw** - Global variable 'w_sys_splash' (w_sys_splash)
- [I] **w_sys_statuscolor.srw** `wf_save` - 'wf_save' lacks try-catch error handling
- [I] **w_sys_statuscolor.srw** - Global variable 'w_sys_statuscolor' (w_sys_statuscolor)
- [I] **w_sys_users.srw** `wf_deletetv` - 'wf_deletetv' lacks try-catch error handling
- [I] **w_sys_users.srw** `wf_getmenu` - 'wf_getmenu' lacks try-catch error handling
- [I] **w_sys_users.srw** `wf_gettvtotal` - 'wf_gettvtotal' lacks try-catch error handling
- [I] **w_sys_users.srw** `wf_savemenu` - 'wf_savemenu' lacks try-catch error handling
- [I] **w_sys_users.srw** `wf_selectall` - 'wf_selectall' lacks try-catch error handling
- [I] **w_sys_users.srw** `wf_setstate` - 'wf_setstate' lacks try-catch error handling
- [I] **w_sys_workrec.srw** - Global variable 'w_sys_workrec' (w_sys_workrec)

## Complexity Hotspots

| Object | Routine | CC | Rating | Lines |
|--------|---------|----|--------|-------|
| w_sngl_btgl_add.srw | wf_save | 27 | D | 80 |
| w_sngl_main.srw | of_get_rpt2 | 22 | D | 80 |
| n_cst_choosefont.sru | choosefont | 22 | D | 108 |
| w_sys_employee_detail.srw | wf_save | 18 | C | 54 |
| w_sngl_items_add.srw | wf_save | 17 | C | 62 |
| w_sngl_sygl_detail.srw | wf_checkout_new | 17 | C | 54 |
| w_sys_data.srw | wf_bf | 16 | C | 67 |
| w_sngl_js_room.srw | wf_roomchangeroom | 16 | C | 42 |
| w_sngl_js_room.srw | wf_jschangeroom | 15 | C | 47 |
| w_sngl_zfgl.srw | wf_sendjs | 15 | C | 40 |
| w_sngl_main.srw | of_get_rpt | 14 | C | 70 |
| w_sngl_sygl_detail.srw | wf_discount_new | 14 | C | 61 |
| w_sngl_main.srw | of_get_dw | 13 | C | 68 |
| w_sys_bellsetting.srw | of_uplaod | 13 | C | 34 |
| w_sys_data.srw | of_export | 12 | C | 32 |
| w_sys_data.srw | of_import | 12 | C | 33 |
| w_sngl_js_begin.srw | wf_setjsbh | 12 | C | 33 |
| w_sngl_zfgl.srw | wf_sendfh | 12 | C | 31 |
| w_sngl_getcardid.srw | wf_key | 11 | C | 41 |
| w_sngl_sygl.srw | wf_room_tab | 11 | C | 28 |

## Inheritance Tree

```
business extends n_cst_business
cb_1 extends commandbutton
cb_13 extends commandbutton
cb_2 extends commandbutton
cb_3 extends commandbutton
cb_4 extends commandbutton
cb_5 extends commandbutton
cb_6 extends commandbutton
cb_7 extends commandbutton
cb_8 extends commandbutton
cb_checkout extends commandbutton
cb_close extends commandbutton
cb_esc extends commandbutton
cb_f2 extends commandbutton
cb_f3 extends commandbutton
cb_f4 extends commandbutton
cb_f5 extends commandbutton
cb_f6 extends commandbutton
cb_new extends commandbutton
cb_refresh extends commandbutton
cb_save extends commandbutton
cb_vip extends commandbutton
cbx_1 extends checkbox
cbx_food extends checkbox
cbx_foodtype extends checkbox
cbx_freefood extends checkbox
cbx_itemtype extends checkbox
cbx_jslevel extends checkbox
cbx_jstype extends checkbox
cbx_mode extends checkbox
cbx_rooms extends checkbox
cbx_welcome extends checkbox
choosefont extends structure
ddlb_1 extends dropdownlistbox
ddlb_bc extends dropdownlistbox
ddplb_1 extends dropdownpicturelistbox
ddplb_2 extends dropdownpicturelistbox
ddplb_mode extends dropdownpicturelistbox
dp_1 extends datepicker
dp_2 extends datepicker
dw_1 extends u_dw
dw_2 extends datawindow
dw_3 extends u_dw
dw_4 extends datawindow
dw_mst extends datawindow
dw_print extends datawindow
em_1 extends editmask
em_2 extends editmask
em_btime extends editmask
em_qz extends editmask
gb_1 extends groupbox
gb_2 extends groupbox
gb_3 extends groupbox
gb_4 extends groupbox
logfont extends structure
m_0 extends menu
m_1开单 extends menu
m_2结算 extends menu
m_3消单 extends menu
m_8入帐 extends menu
m_9其他 extends menu
m_btgl_main extends menu
m_sngl_sygl extends menu
m_vip卡充值 extends menu
m_vip卡明晰 extends menu
m_vip操作 extends menu
m_zkgl_main extends menu
m_交班 extends menu
m_余额查询 extends menu
m_修改房态 extends menu
m_充值记录 extends menu
m_其他操作 extends menu
m_吧台操作 extends menu
m_帮助主题 extends menu
m_撤分 extends menu
m_收银管理 extends menu
m_新增预定 extends menu
m_消费入帐 extends menu
m_消费查询 extends menu
m_清除状态 extends menu
m_窗口布局 extends menu
m_系统工具 extends menu
m_系统帮助 extends menu
m_组合 extends menu
m_退出 extends menu
m_销售 extends menu
m_预定 extends menu
m_预留列表 extends menu
mdi_1 extends mdiclient
mle_1 extends multilineedit
n_cst_choosefont extends nonvisualobject
of_systemerror extends function_object
p_1 extends picture
p_2 extends picture
pb_1 extends picturebutton
rb_1 extends radiobutton
rb_2 extends radiobutton
rect extends structure
size extends structure
sle_1 extends singlelineedit
sle_2 extends singlelineedit
sle_3 extends singlelineedit
sle_4 extends singlelineedit
sle_5 extends singlelineedit
sle_class extends singlelineedit
sle_dbname extends singlelineedit
sle_fh extends singlelineedit
sle_id extends singlelineedit
sle_js extends singlelineedit
sle_new extends singlelineedit
sle_newjs extends singlelineedit
sle_old extends singlelineedit
sle_oldjs extends singlelineedit
sle_pass extends singlelineedit
sle_password extends singlelineedit
sle_renew extends singlelineedit
sle_room extends singlelineedit
sle_room_new extends singlelineedit
sle_roomid extends singlelineedit
sle_servername extends singlelineedit
sle_time extends singlelineedit
sle_username extends singlelineedit
sle_zs extends singlelineedit
st_1 extends statictext
st_10 extends statictext
st_2 extends statictext
st_3 extends statictext
st_4 extends statictext
st_5 extends statictext
st_6 extends statictext
st_7 extends statictext
st_8 extends statictext
st_9 extends statictext
st_bc extends statictext
st_cust extends statictext
st_help extends statictext
st_horizontal extends u_splitbar_horizontal
st_rq extends statictext
st_sn extends statictext
st_ver extends statictext
st_vertical extends u_splitbar_vertical
str_minmaxinfo extends structure
str_point extends structure
tab_1 extends tab
tabpage_1 extends userobject
tabpage_2 extends userobject
tabpage_3 extends userobject
tv_list extends treeview
uf_get_fresh extends function_object
uf_get_roomtips extends function_object
uf_getmodarr extends function_object
uf_print_grid_ds extends function_object
uf_zf_hfqz extends function_object
uf_zf_openroom extends function_object
uf_zf_tip extends function_object
uf_zf_zs extends function_object
uo_1 extends u_query_single
uo_query extends u_query_single
uo_toolbar extends u_cst_toolbar
w_js_base extends window
w_list_jszs extends window
w_list_jszs_history extends window
w_list_jszs_tj extends window
w_list_jszs_tj_history extends window
w_list_kstj extends window
w_list_kstj_history extends window
w_list_missworks extends window
w_list_missworks_history extends window
w_list_orders extends window
w_list_orders_history extends window
w_list_srfx extends window
w_sngl_btgl extends window
w_sngl_btgl_add extends window
w_sngl_checkout_fwf extends window
w_sngl_checkout_getfh extends window
w_sngl_checkout_js extends window
w_sngl_checkout_pay3 extends window
w_sngl_getcardid extends window
w_sngl_getfh extends window
w_sngl_getjs extends w_js_base
w_sngl_getjs_insert extends window
w_sngl_getzs extends w_js_base
w_sngl_group extends window
w_sngl_group_fc extends window
w_sngl_items_add extends w_js_base
w_sngl_jb_opter extends window
w_sngl_js_add extends w_js_base
w_sngl_js_atten extends window
w_sngl_js_begin extends w_js_base
w_sngl_js_div extends w_js_base
w_sngl_js_end extends w_js_base
w_sngl_js_groupid extends window
w_sngl_js_js extends w_js_base
w_sngl_js_mode extends w_js_base
w_sngl_js_new extends w_js_base
w_sngl_js_query extends window
w_sngl_js_res extends window
w_sngl_js_reslist extends window
w_sngl_js_room extends w_js_base
w_sngl_js_rs extends window
w_sngl_js_status extends window
w_sngl_lmgl_rmst extends window
w_sngl_main extends window
w_sngl_payment extends window
w_sngl_res_call extends window
w_sngl_res_new extends window
w_sngl_rj_opter extends window
w_sngl_sygl extends window
w_sngl_sygl_detail extends window
w_sngl_zfgl extends window
w_sngl_zkgl_rmst extends window
w_sys_about extends window
w_sys_accbills extends window
w_sys_accbills_audit_list extends window
w_sys_accbills_list extends window
w_sys_accitems extends window
w_sys_addtype extends window
w_sys_background extends window
w_sys_bellsetting extends window
w_sys_busy extends window
w_sys_caller extends window
w_sys_changepas extends window
w_sys_connectinfo extends window
w_sys_data extends window
w_sys_employee_detail extends window
w_sys_employee_list extends window
w_sys_employee_stype extends window
w_sys_getrq extends window
w_sys_getrq2 extends window
w_sys_getrq3 extends window
w_sys_getyf extends window
w_sys_items_list extends window
w_sys_jsgz extends window
w_sys_jsgz_list extends window
w_sys_log extends window
w_sys_login extends window
w_sys_missesold_detail extends window
w_sys_missitems_detail extends window
w_sys_missitems_list extends window
w_sys_missitemstype extends window
w_sys_payment extends window
w_sys_rooms_detail extends window
w_sys_rooms_list extends window
w_sys_roomtype extends window
w_sys_roomtype_detail extends window
w_sys_roomtype_list extends window
w_sys_setbg extends window
w_sys_splash extends window
w_sys_statuscolor extends window
w_sys_users extends window
w_sys_workrec extends window
```

## Cross-Object Dependencies

| Object | Depends On |
|--------|-----------|
| m_btgl_main.srm | THIS, call, m_0, m_吧台操作, m_消费入帐 |
| m_sngl_sygl.srm | call, m_, m_1开单, m_2结算, m_3消单 |
| m_zkgl_main.srm | call, m_zkgl_main, m_修改房态, m_其他操作, m_新增预定 |
| n_cst_choosefont.sru | TriggerEvent, call, nonvisualobject, structure |
| of_systemerror.srf | function_object |
| rect.srs | structure |
| uf_get_fresh.srf | function_object |
| uf_get_roomtips.srf | function_object |
| uf_getmodarr.srf | function_object |
| uf_print_grid_ds.srf | compute, function_object, line |
| uf_zf_hfqz.srf | function_object |
| uf_zf_openroom.srf | function_object |
| uf_zf_tip.srf | function_object |
| uf_zf_zs.srf | function_object |
| w_js_base.srw | end, window |
| w_list_jszs.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_list_jszs_history.srw | cb_2, cb_3, cb_4, cb_5, commandbutton |
| w_list_jszs_tj.srw | cb_1, cb_2, cb_3, commandbutton, dw_1 |
| w_list_jszs_tj_history.srw | cb_1, cb_2, cb_3, commandbutton, dw_1 |
| w_list_kstj.srw | cb_1, cb_2, commandbutton, d_rpt_rj_kstj_graph, datawindow |
| w_list_kstj_history.srw | cb_1, cb_2, commandbutton, d_rpt_rj_kstj_graph_histroy, datawindow |
| w_list_missworks.srw | cb_1, cb_2, commandbutton, d_list_missworks, d_rpt_rj_js |
| w_list_missworks_history.srw | cb_1, cb_2, commandbutton, d_list_missworks_all, d_rpt_rj_js |
| w_list_orders.srw | cb_1, cb_2, cb_4, commandbutton, d_list_orders |
| w_list_orders_history.srw | cb_1, cb_2, cb_4, commandbutton, d_list_orders |
| w_list_srfx.srw | cb_2, cb_4, commandbutton, d_rpt_rj_srfx_graph, d_rpt_rj_srfx_group |
| w_sngl_btgl.srw | d_btgl_orders_itemsOK_list, d_btgl_orders_items_list, d_room_status, datawindow, dw_1 |
| w_sngl_btgl_add.srw | cb_close, cb_new, cb_save, commandbutton, d_btgl_item_input |
| w_sngl_checkout_fwf.srw | cb_1, cb_2, commandbutton, singlelineedit, sle_1 |
| w_sngl_checkout_getfh.srw | cb_1, cb_2, commandbutton, singlelineedit, sle_1 |
| w_sngl_checkout_js.srw | cb_1, cb_2, cbx_1, checkbox, commandbutton |
| w_sngl_checkout_pay3.srw | business, call, cb_1, cb_2, cb_4 |
| w_sngl_getcardid.srw | cb_1, cb_2, commandbutton, singlelineedit, sle_1 |
| w_sngl_getfh.srw | cb_1, cb_2, commandbutton, singlelineedit, sle_1 |
| w_sngl_getjs.srw | cb_1, cb_2, commandbutton, int, none |
| w_sngl_getjs_insert.srw | cb_1, cb_2, commandbutton, none, singlelineedit |
| w_sngl_getzs.srw | call, cb_1, cb_2, commandbutton, none |
| w_sngl_group.srw | cb_1, cb_2, cb_esc, cb_f2, cb_f4 |
| w_sngl_group_fc.srw | cb_1, cb_2, cb_esc, cb_f2, cb_f4 |
| w_sngl_items_add.srw | cb_close, cb_new, cb_save, commandbutton, d_item_input |
| w_sngl_jb_opter.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sngl_js_add.srw | cb_1, cb_2, commandbutton, int, none |
| w_sngl_js_atten.srw | cb_1, cb_2, cb_esc, cb_f2, cb_f3 |
| w_sngl_js_begin.srw | cb_1, cb_2, cb_3, cbx_1, checkbox |
| w_sngl_js_div.srw | call, cb_1, cb_2, commandbutton, none |
| w_sngl_js_end.srw | cb_1, cb_2, commandbutton, int, singlelineedit |
| w_sngl_js_groupid.srw | cb_1, cb_2, commandbutton, none, singlelineedit |
| w_sngl_js_js.srw | cb_1, cb_2, commandbutton, ddplb_mode, dropdownpicturelistbox |
| w_sngl_js_mode.srw | cb_1, cb_2, commandbutton, ddplb_1, ddplb_2 |
| w_sngl_js_new.srw | cb_1, cb_2, cbx_1, checkbox, commandbutton |
| w_sngl_js_query.srw | d_miss_query, datawindow, dw_1, none, window |
| w_sngl_js_res.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sngl_js_reslist.srw | cb_1, cb_2, cb_3, commandbutton, d_res_list |
| w_sngl_js_room.srw | cb_1, cb_2, commandbutton, int, none |
| w_sngl_js_rs.srw | cb_1, cb_2, commandbutton, none, singlelineedit |
| w_sngl_js_status.srw | cb_1, cb_2, commandbutton, none, singlelineedit |
| w_sngl_lmgl_rmst.srw | cb_1, cb_2, cb_3, cb_4, cb_5 |
| w_sngl_main.srw | datastore, if, m_sngl_main, mdi_1, mdiclient |
| w_sngl_payment.srw | cb_2, cb_3, commandbutton, d_payment_list, datawindow |
| w_sngl_res_call.srw | cb_1, cb_2, cbx_1, checkbox, commandbutton |
| w_sngl_res_new.srw | cb_1, cb_2, cb_3, commandbutton, editmask |
| w_sngl_rj_opter.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sngl_sygl.srw | d_billitems_list, d_bills_lg_list, datawindow, dw_1, dw_2 |
| w_sngl_sygl_detail.srw | cb_1, cb_2, cb_3, cb_checkout, cb_esc |
| w_sngl_zfgl.srw | d_miss_works, d_resOK_list, d_reswt_list, datawindow, dw_1 |
| w_sngl_zkgl_rmst.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_about.srw | cb_1, commandbutton, gb_1, groupbox, mle_1 |
| w_sys_accbills.srw | cb_1, cb_2, cb_3, cb_4, cb_5 |
| w_sys_accbills_audit_list.srw | cb_1, cb_3, cb_4, commandbutton, d_accbills_audit_list |
| w_sys_accbills_list.srw | cb_2, cb_3, cb_4, commandbutton, d_accbills_list |
| w_sys_accitems.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_addtype.srw | cb_1, cb_2, commandbutton, singlelineedit, sle_1 |
| w_sys_background.srw | datawindow, dw_1, this, window |
| w_sys_bellsetting.srw | cb_13, cb_2, cb_6, cbx_food, cbx_foodtype |
| w_sys_busy.srw | st_1, statictext, window |
| w_sys_caller.srw | cb_1, cb_close, cb_new, cb_save, commandbutton |
| w_sys_changepas.srw | cb_1, cb_2, commandbutton, gb_1, groupbox |
| w_sys_connectinfo.srw | cb_1, cb_close, commandbutton, gb_1, groupbox |
| w_sys_data.srw | cb_1, cb_2, cb_3, commandbutton, datastore |
| w_sys_employee_detail.srw | cb_1, cb_2, cb_close, cb_new, cb_save |
| w_sys_employee_list.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_employee_stype.srw | cb_1, cb_close, cb_new, cb_save, commandbutton |
| w_sys_getrq.srw | cb_1, cb_2, commandbutton, datepicker, ddlb_1 |
| w_sys_getrq2.srw | cb_1, cb_2, commandbutton, datepicker, dp_1 |
| w_sys_getrq3.srw | cb_1, cb_2, commandbutton, datepicker, ddlb_bc |
| w_sys_getyf.srw | cb_1, cb_2, commandbutton, datepicker, dp_1 |
| w_sys_items_list.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_jsgz.srw | cb_close, cb_new, cb_save, commandbutton, d_sys_jsgz |
| w_sys_jsgz_list.srw | cb_1, cb_3, cb_4, commandbutton, d_sys_jsgz_setup |
| w_sys_log.srw | cb_1, cb_2, cb_3, commandbutton, d_sys_log |
| w_sys_login.srw | cb_1, cb_2, cb_3, commandbutton, gb_1 |
| w_sys_missesold_detail.srw | cb_1, cb_close, cb_save, commandbutton, d_sys_missesold_detail |
| w_sys_missitems_detail.srw | cb_close, cb_new, cb_save, commandbutton, d_sys_missitems_detail |
| w_sys_missitems_list.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_missitemstype.srw | cb_1, cb_close, cb_new, cb_save, commandbutton |
| w_sys_payment.srw | cb_1, cb_close, cb_new, cb_save, commandbutton |
| w_sys_rooms_detail.srw | cb_close, cb_new, cb_save, commandbutton, d_sys_rooms_detail |
| w_sys_rooms_list.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_roomtype.srw | cb_1, cb_close, cb_new, cb_save, commandbutton |
| w_sys_roomtype_detail.srw | cb_close, cb_new, cb_save, commandbutton, d_sys_roomtype_detail |
| w_sys_roomtype_list.srw | cb_1, cb_2, cb_3, cb_4, commandbutton |
| w_sys_setbg.srw | cb_1, cb_2, cb_3, cb_4, cb_5 |
| w_sys_splash.srw | datawindow, dw_1, this, window |
| w_sys_statuscolor.srw | cb_1, cb_close, cb_save, commandbutton, d_sys_statuscolor |
| w_sys_users.srw | cb_1, cb_2, cb_3, cb_4, cb_5 |
| w_sys_workrec.srw | cb_1, cb_2, cb_5, commandbutton, d_sys_workrec |

## File Details

| File | Type | Routines | Variables | Size |
|------|------|----------|-----------|------|
| of_systemerror.srf | srf | 1 | 0 | 801 B |
| p_dgsauna_exe.srj | srj | 0 | 0 | 19.9 KB |
| rect.srs | srs | 0 | 0 | 100 B |
| uf_get_fresh.srf | srf | 1 | 0 | 362 B |
| uf_get_roomtips.srf | srf | 1 | 0 | 328 B |
| uf_getmodarr.srf | srf | 1 | 0 | 919 B |
| uf_print_grid_ds.srf | srf | 1 | 0 | 7.8 KB |
| w_list_jszs.srw | srw | 0 | 1 | 6.0 KB |
| w_list_jszs_history.srw | srw | 0 | 1 | 6.5 KB |
| w_list_jszs_tj.srw | srw | 0 | 1 | 3.5 KB |
| w_list_jszs_tj_history.srw | srw | 0 | 1 | 3.5 KB |
| w_list_kstj.srw | srw | 1 | 1 | 6.5 KB |
| w_list_kstj_history.srw | srw | 1 | 1 | 6.3 KB |
| w_list_missworks.srw | srw | 0 | 1 | 5.4 KB |
| w_list_missworks_history.srw | srw | 0 | 1 | 6.4 KB |
| w_list_orders.srw | srw | 0 | 1 | 7.9 KB |
| w_list_orders_history.srw | srw | 0 | 1 | 8.1 KB |
| w_list_srfx.srw | srw | 1 | 1 | 7.5 KB |
| w_sngl_getcardid.srw | srw | 4 | 1 | 5.8 KB |
| w_sngl_getfh.srw | srw | 0 | 1 | 3.7 KB |
| w_sngl_group.srw | srw | 4 | 1 | 10.9 KB |
| w_sngl_group_fc.srw | srw | 4 | 1 | 11.0 KB |
| w_sngl_main.srw | srw | 10 | 0 | 13.1 KB |
| w_sys_about.srw | srw | 0 | 1 | 8.7 KB |
| w_sys_background.srw | srw | 2 | 1 | 5.3 KB |
| w_sys_busy.srw | srw | 0 | 1 | 943 B |
| w_sys_changepas.srw | srw | 0 | 1 | 6.9 KB |
| w_sys_connectinfo.srw | srw | 1 | 1 | 8.4 KB |
| w_sys_data.srw | srw | 8 | 1 | 21.8 KB |
| w_sys_getrq.srw | srw | 1 | 1 | 7.5 KB |
| w_sys_getrq2.srw | srw | 0 | 1 | 4.7 KB |
| w_sys_getrq3.srw | srw | 0 | 1 | 6.7 KB |
| w_sys_getyf.srw | srw | 1 | 1 | 4.4 KB |
| w_sys_login.srw | srw | 0 | 1 | 9.5 KB |
| w_sys_setbg.srw | srw | 1 | 1 | 13.1 KB |
| w_sys_splash.srw | srw | 0 | 1 | 3.5 KB |
| d_res_detail.srd | srd | 0 | 0 | 15.1 KB |
| d_res_list.srd | srd | 0 | 0 | 22.3 KB |
| d_resok_list.srd | srd | 0 | 0 | 27.2 KB |
| d_reswt_list.srd | srd | 0 | 0 | 25.4 KB |
| m_zkgl_main.srm | srm | 0 | 1 | 7.3 KB |
| w_sngl_res_call.srw | srw | 0 | 1 | 12.1 KB |
| w_sngl_res_new.srw | srw | 0 | 1 | 10.0 KB |
| w_sngl_zkgl_rmst.srw | srw | 0 | 1 | 5.8 KB |
| d_btgl_item_input.srd | srd | 0 | 0 | 22.4 KB |
| d_btgl_orders_items_list.srd | srd | 0 | 0 | 28.3 KB |
| d_btgl_orders_itemsok_list.srd | srd | 0 | 0 | 30.4 KB |
| m_btgl_main.srm | srm | 0 | 1 | 6.2 KB |
| w_sngl_btgl.srw | srw | 4 | 0 | 8.3 KB |
| w_sngl_btgl_add.srw | srw | 3 | 1 | 13.7 KB |
| w_sngl_lmgl_rmst.srw | srw | 0 | 1 | 9.2 KB |
| uf_zf_hfqz.srf | srf | 1 | 0 | 643 B |
| uf_zf_openroom.srf | srf | 1 | 0 | 821 B |
| uf_zf_tip.srf | srf | 1 | 0 | 1.5 KB |
| uf_zf_zs.srf | srf | 1 | 0 | 868 B |
| w_js_base.srw | srw | 2 | 1 | 819 B |
| w_sngl_getjs.srw | srw | 1 | 1 | 4.3 KB |
| w_sngl_getjs_insert.srw | srw | 0 | 1 | 6.4 KB |
| w_sngl_getzs.srw | srw | 1 | 1 | 3.9 KB |
| w_sngl_js_add.srw | srw | 1 | 1 | 9.9 KB |
| w_sngl_js_atten.srw | srw | 1 | 1 | 11.0 KB |
| w_sngl_js_begin.srw | srw | 2 | 1 | 18.4 KB |
| w_sngl_js_div.srw | srw | 1 | 1 | 9.8 KB |
| w_sngl_js_end.srw | srw | 1 | 1 | 7.8 KB |
| w_sngl_js_groupid.srw | srw | 0 | 1 | 9.6 KB |
| w_sngl_js_js.srw | srw | 1 | 1 | 13.1 KB |
| w_sngl_js_mode.srw | srw | 2 | 1 | 11.8 KB |
| w_sngl_js_new.srw | srw | 1 | 1 | 6.7 KB |
| w_sngl_js_query.srw | srw | 1 | 1 | 1.6 KB |
| w_sngl_js_res.srw | srw | 2 | 1 | 10.5 KB |
| w_sngl_js_reslist.srw | srw | 2 | 1 | 5.1 KB |
| w_sngl_js_room.srw | srw | 4 | 1 | 15.8 KB |
| w_sngl_js_rs.srw | srw | 0 | 1 | 5.4 KB |
| w_sngl_js_status.srw | srw | 0 | 1 | 9.3 KB |
| w_sngl_zfgl.srw | srw | 12 | 0 | 24.7 KB |
| m_sngl_sygl.srm | srm | 0 | 1 | 25.8 KB |
| w_sngl_checkout_fwf.srw | srw | 0 | 1 | 3.6 KB |
| w_sngl_checkout_getfh.srw | srw | 0 | 1 | 3.9 KB |
| w_sngl_checkout_js.srw | srw | 0 | 1 | 14.5 KB |
| w_sngl_checkout_pay3.srw | srw | 3 | 1 | 22.2 KB |
| w_sngl_items_add.srw | srw | 4 | 1 | 12.0 KB |
| w_sngl_jb_opter.srw | srw | 0 | 1 | 7.5 KB |
| w_sngl_payment.srw | srw | 2 | 1 | 5.5 KB |
| w_sngl_rj_opter.srw | srw | 0 | 1 | 6.3 KB |
| w_sngl_sygl.srw | srw | 10 | 0 | 16.9 KB |
| w_sngl_sygl_detail.srw | srw | 8 | 1 | 17.0 KB |
| d_sys_userrole.srd | srd | 0 | 0 | 4.5 KB |
| d_sys_users.srd | srd | 0 | 0 | 22.7 KB |
| d_sys_workrec.srd | srd | 0 | 0 | 18.8 KB |
| d_sysset.srd | srd | 0 | 0 | 8.0 KB |
| ddw_roomtype.srd | srd | 0 | 0 | 5.2 KB |
| n_cst_choosefont.sru | sru | 1 | 0 | 4.9 KB |
| w_sys_addtype.srw | srw | 0 | 1 | 3.5 KB |
| w_sys_bellsetting.srw | srw | 4 | 1 | 12.9 KB |
| w_sys_caller.srw | srw | 2 | 1 | 5.1 KB |
| w_sys_employee_detail.srw | srw | 4 | 1 | 12.6 KB |
| w_sys_employee_list.srw | srw | 1 | 1 | 8.4 KB |
| w_sys_employee_stype.srw | srw | 2 | 1 | 6.0 KB |
| w_sys_items_list.srw | srw | 0 | 1 | 7.4 KB |
| w_sys_jsgz.srw | srw | 3 | 1 | 6.9 KB |
| w_sys_jsgz_list.srw | srw | 1 | 1 | 7.5 KB |
| w_sys_log.srw | srw | 0 | 1 | 3.9 KB |
| w_sys_missesold_detail.srw | srw | 1 | 1 | 6.1 KB |
| w_sys_missitems_detail.srw | srw | 2 | 1 | 6.1 KB |
| w_sys_missitems_list.srw | srw | 1 | 1 | 8.1 KB |
| w_sys_missitemstype.srw | srw | 2 | 1 | 5.5 KB |
| w_sys_payment.srw | srw | 2 | 1 | 5.6 KB |
| w_sys_rooms_detail.srw | srw | 2 | 1 | 5.4 KB |
| w_sys_rooms_list.srw | srw | 1 | 1 | 8.1 KB |
| w_sys_roomtype.srw | srw | 2 | 1 | 5.1 KB |
| w_sys_roomtype_detail.srw | srw | 1 | 0 | 5.3 KB |
| w_sys_roomtype_list.srw | srw | 0 | 1 | 7.7 KB |
| w_sys_statuscolor.srw | srw | 1 | 1 | 4.5 KB |
| w_sys_users.srw | srw | 7 | 0 | 16.3 KB |
| w_sys_workrec.srw | srw | 0 | 1 | 5.6 KB |
| d_orders_print_std.srd | srd | 0 | 0 | 20.6 KB |
| d_orders_print_view.srd | srd | 0 | 0 | 43.7 KB |
| d_rpt_acc_accbills_total.srd | srd | 0 | 0 | 28.8 KB |
| d_rpt_acc_caller_job.srd | srd | 0 | 0 | 22.2 KB |
| d_rpt_acc_checkout.srd | srd | 0 | 0 | 13.5 KB |
| d_rpt_acc_checkout_110mm.srd | srd | 0 | 0 | 36.0 KB |
| d_rpt_acc_checkout_58mm.srd | srd | 0 | 0 | 35.9 KB |
| d_rpt_acc_checkout_60mm.srd | srd | 0 | 0 | 35.9 KB |
| d_rpt_acc_checkout_80mm.srd | srd | 0 | 0 | 35.9 KB |
| d_rpt_acc_items.srd | srd | 0 | 0 | 36.2 KB |
| d_rpt_acc_items_bak.srd | srd | 0 | 0 | 44.2 KB |
| d_rpt_acc_js.srd | srd | 0 | 0 | 32.1 KB |
| d_rpt_acc_js_total.srd | srd | 0 | 0 | 18.3 KB |
| d_rpt_acc_js_total_new.srd | srd | 0 | 0 | 10.5 KB |
| d_rpt_acc_js_total_zs.srd | srd | 0 | 0 | 18.3 KB |
| d_rpt_acc_orders.srd | srd | 0 | 0 | 59.0 KB |
| d_rpt_acc_record_list.srd | srd | 0 | 0 | 75.0 KB |
| d_rpt_js_total.srd | srd | 0 | 0 | 5.7 KB |
| d_rpt_js_zb.srd | srd | 0 | 0 | 5.7 KB |
| d_rpt_rj_caller_job.srd | srd | 0 | 0 | 22.1 KB |
| d_rpt_rj_checkout.srd | srd | 0 | 0 | 13.5 KB |
| d_rpt_rj_checkout_110mm.srd | srd | 0 | 0 | 35.9 KB |
| d_rpt_rj_checkout_58mm.srd | srd | 0 | 0 | 35.8 KB |
| d_rpt_rj_checkout_60mm.srd | srd | 0 | 0 | 35.9 KB |
| d_rpt_rj_checkout_80mm.srd | srd | 0 | 0 | 35.9 KB |
| d_rpt_rj_items.srd | srd | 0 | 0 | 36.1 KB |
| d_rpt_rj_js.srd | srd | 0 | 0 | 32.1 KB |
| d_rpt_rj_js_total.srd | srd | 0 | 0 | 18.3 KB |
| d_rpt_rj_js_total_new.srd | srd | 0 | 0 | 10.4 KB |
| d_rpt_rj_js_total_zs.srd | srd | 0 | 0 | 18.3 KB |
| d_rpt_rj_orders.srd | srd | 0 | 0 | 39.2 KB |
| d_rpt_rj_record_list.srd | srd | 0 | 0 | 74.9 KB |
| d_accbills_audit_list.srd | srd | 0 | 0 | 18.0 KB |
| d_accbills_detail.srd | srd | 0 | 0 | 43.1 KB |
| d_accbills_list.srd | srd | 0 | 0 | 18.0 KB |
| d_accitems_list.srd | srd | 0 | 0 | 14.7 KB |
| ddw_accitems_list.srd | srd | 0 | 0 | 7.4 KB |
| w_sys_accbills.srw | srw | 0 | 1 | 10.7 KB |
| w_sys_accbills_audit_list.srw | srw | 1 | 1 | 5.9 KB |
| w_sys_accbills_list.srw | srw | 1 | 1 | 6.4 KB |
| w_sys_accitems.srw | srw | 0 | 1 | 4.7 KB |

**Total source size:** 2154.8 KB
