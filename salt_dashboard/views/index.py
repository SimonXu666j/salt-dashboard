#coding=UTF-8
import datetime
import os
import re
import md5
import json



from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.template import RequestContext

from salt_dashboard.api import salt_api,common
from django.db import connection

def auto(request):
    context = {}
    context.update(csrf(request))
    return render_to_response('auto_sidebar.html', context)


def overview(request):
    context = {}
    context.update(csrf(request))
    grains = salt_api.overview(request).values()
    minions_os = {}
    minions_virtual = {}
    for grain in grains:
        try:
            minions_os[grain['osfullname']+grain['osrelease']] += 1
            minions_virtual[grain['virtual']] += 1
        except KeyError:
            minions_os[grain['osfullname']+grain['osrelease']] = 1
            minions_virtual[grain['virtual']] = 1
    try:
        cursor = connection.cursor()
        host_num = cursor.execute("select id,fun,time,success from  \
		(select id,fun,time,success from salt.salt_returns where \
		success='0' order by id desc) as b group by id limit 10;")
        hosts = cursor.fetchall()
        error_host = []
        for host in hosts:
            error_host.append({
              'id':host[0],
              'fun':host[1],
              'time':host[2],
              'success':host[3]
              })
    except:
        error_host = []


    context['minions_os'] = minions_os
    context['minions_virtual'] = minions_virtual
    context['minions_num'] = len(grains)
    context['error_host'] = error_host
    return render_to_response('auto_overview.html', context)

def minions(request):
    current_page = int(request.GET.get("page",0))
    page_sum = 15
    page_extra = 3
    grains = salt_api.overview(request).values()
    try:
        cursor = connection.cursor()
        host_num = cursor.execute('select host_id,time from \
            (select host_id,time from fluent.salt_result order \
            by id desc ) as b group by host_id;')
        hosts_time = cursor.fetchall()
        now = datetime.datetime.now()
        times_diff = {}
        for host_time in hosts_time:
           time_dist = now - host_time[1] 
           times_diff[host_time[0]] = str(time_dist).split('.')[0]
    except:
        times_diff = {}
    for grain in grains:
        grain['IP'] = grain['id'].split('.')[0].replace('_','.')
        grain['time_diff'] = times_diff.get(grain['id'],'无')
    context = common.my_page(request,len(grains))
    context['page_tables'] = grains[current_page*page_sum:(current_page+1)*page_sum]
    return render_to_response('auto_minions.html', context)

def execute(request):
    context = {'jid':''}
    tgt = request.POST.get('tgt','*')
    fun = request.POST.get('fun','cmd.run')
    arg = request.POST.get('arg','')
    if arg:
        kwargs = {'tgt': tgt,
              'ret': 'mysql',
              'expr_form': 'glob',
              'timeout': 15,
              'arg': [arg],
              'fun': fun
              }
        jid = salt_api.execute(**kwargs)
    context['jid'] = jid
    return render_to_response('auto_execute.html', context)

def detail(request):
    target = request.GET.get('target','')
    if target:
        grain = salt_api.overview(request)
        state = salt_api.get_state(target)
    state = repr(json.dumps(state,sort_keys=True, indent=4))
    state = state.replace('\\n','<br/>').replace(' ','&nbsp;')
    context = {
            'grain':grain,
            'state':state
        }
    return render_to_response('auto_detail.html', context)

def getjobinfo(request):
    context = {}
    jid = request.GET.get('jid','')
    where = int(request.GET.get('where','12376894567235'))
    if where == 12376894567235:
        result = '/getjobinfo?jid=%s&where=%s' % (jid,0)
        return HttpResponse(result)
    else:
        cursor = connection.cursor()
        host_result = cursor.execute("select id,success,`return` from salt.salt_returns \
            where jid='%s' limit %s,10000;" % (jid,where) )
        hosts_result = cursor.fetchall()
        where = len(hosts_result) + where
        result = []
        for host_result in hosts_result:
            result.append(u'host:%s&nbsp;&nbsp;&nbsp;state:%s<br/>return:%s<br/>' % (host_result[0],host_result[1],host_result[2]))
        context = {
              "where":where,
              "result":result
            }
    return HttpResponse(json.dumps(context))
