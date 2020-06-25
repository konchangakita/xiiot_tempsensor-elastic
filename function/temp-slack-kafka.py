import logging
import json
import urllib3
urllib3.disable_warnings()
import datetime

# send slack
def send_slack(rmsg):
    http = urllib3.PoolManager()
    # Slack channel "#xi-iot温度計"
    url = 'https://hooks.slack.com/services/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'
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    method = 'POST'


    # set massage
    slack_msg = ":fire:【温度注意報】制限値"+str(rmsg["limit_t"])+"度を越えています。:snowman: \n"+str(rmsg["hotcold"])+"! 現在の温度: "+str(rmsg["temperature"])+"℃, 湿度: "+str(rmsg["humidity"])+"% ("+str(rmsg["now_dt"])+")"

    data = {
        "text": slack_msg
    }

    json_data = json.dumps(data).encode("utf-8")
    req = http.request(url=url, body=json_data, headers=headers, method=method)

    #logging.info(json.loads(req.data.decode('utf-8')))

def main(ctx, msg):  
    logging.info("Parameters: %s", ctx.get_config())
    logging.info("Receive msg from %s", ctx.get_topic())
    
    rmsg = json.loads(msg)
    
    # input parameter
    param = ctx.get_config()
    rmsg["limit_upper"] = int(param["limit_upper"])
    rmsg["limit_under"] = int(param["limit_under"])
    now1 = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) # Japan time
    rmsg['now_dt'] = "{0:%Y-%m-%d %H:%M:%S }".format(now1) + str(now1.tzinfo)

    # parameter judgement 
    if rmsg["temperature"] > rmsg["limit_upper"]:
        # send to slack
        rmsg["hotcold"] = "あっちぃ"
        rmsg["limit_t"] = rmsg["limit_upper"]
        send_slack(rmsg)
    elif rmsg["temperature"] < rmsg["limit_under"]:
        rmsg["hotcold"] = "寒いよ"
        rmsg["limit_t"] = rmsg["limit_under"]        
        send_slack(rmsg)

    
    # Forward to next stage in pipeline.
    logging.info("rmsg: %s", rmsg)
    rmsg = json.dumps(rmsg).encode('utf-8') #python3
    ctx.send(rmsg)