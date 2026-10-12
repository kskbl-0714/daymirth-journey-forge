"""Exercise generic counts, input boundaries, and private-ticket exclusion."""
import copy
import json
import tempfile
from pathlib import Path
from validate_trip import validate
from build_app import generate, SKILL
from verify_output import verify


def main():
    sample=SKILL/"examples/fictional-trip";data=json.loads((sample/"trip.json").read_text(encoding="utf-8"));checks=[]
    def expect(ok,label):
        if not ok:raise AssertionError(label)
        checks.append(label)
    with tempfile.TemporaryDirectory(prefix="daymirth-selftest-") as temp:
        temp=Path(temp)
        many=copy.deepcopy(data);many["travelers"]=[{"id":f"traveler-{i}","displayName":f"使用者 {i}"} for i in range(57)];many["tickets"]=[{"id":f"ticket-{i}","title":f"票据 {i}","mimeType":"application/pdf","file":"tickets/fictional-ferry.pdf","eventIds":["d01-e01-north-harbor"],"travelerIds":[t["id"] for t in many["travelers"]],"notes":"Fictional demo"} for i in range(203)]
        expect(not validate(many,sample)[0],"57 travelers / 203 shared multi-person tickets validate")
        many["app"]["name"]="中文 App <script>window.attacked=true</script>";inputfile=temp/"many.json";inputfile.write_text(json.dumps(many,ensure_ascii=False),encoding="utf-8");out=generate(inputfile,sample,temp/"many-out")
        generated=json.loads((out/"web/trip.json").read_text(encoding="utf-8"));expect(len(generated["travelers"])==57 and len(generated["tickets"])==203,"arbitrary counts survive generation")
        expect(not list((out/"web").glob("tickets/*")),"default PWA contains no private ticket bytes")
        expect(all("file" not in t and t["deliveryMode"]=="local-import" for t in generated["tickets"]),"all ticket slots convert to local import")
        expect("<script>window.attacked" not in (out/"web/index.html").read_text(encoding="utf-8"),"App title escapes executable HTML")
        expect(not verify(out/"web")[0],"generated output is complete")
        for bad in ("tickets/../secret.pdf","tickets/%2e%2e/secret.pdf","C:/secret.pdf","https://example.org/ticket.pdf","tickets/sub/../../secret.pdf"):
            invalid=copy.deepcopy(data);invalid["tickets"][0]["file"]=bad;expect(bool(validate(invalid,sample)[0]),"reject unsafe path "+bad)
        invalid=copy.deepcopy(data);invalid["days"][1]["events"][0]["id"]=invalid["days"][0]["events"][0]["id"];expect(bool(validate(invalid,sample)[0]),"reject duplicate stable event IDs")
        invalid=copy.deepcopy(data);invalid["days"][0]["events"][0]["coordinates"]={"lat":91,"lng":0};expect(bool(validate(invalid,sample)[0]),"reject invalid coordinates")
        bare={"schemaVersion":1,"tripId":"bare-trip","app":{"language":"en"},"days":[{"id":"day-1","title":"Unscheduled","events":[{"id":"event-1","title":"No tickets, photo, date, time or coordinates"}]}]}
        inputfile=temp/"bare.json";inputfile.write_text(json.dumps(bare),encoding="utf-8");out=generate(inputfile,temp,temp/"bare-out");expect(not verify(out/"web")[0],"minimal trip generates without optional inputs")
        expect(json.loads((out/"web/trip.json").read_text())["app"]["name"]=="TripPocket","App name defaults to TripPocket")
    print(json.dumps({"passed":len(checks),"checks":checks},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
