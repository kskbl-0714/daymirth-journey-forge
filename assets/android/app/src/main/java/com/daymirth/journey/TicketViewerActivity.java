package com.daymirth.journey;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.pdf.PdfRenderer;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

/** Bundled ticket viewer: dynamic documents, PDF pages, pinch/pan, and swipe. */
public class TicketViewerActivity extends Activity {
    private JSONArray tickets;
    private int document=0, page=0, count=1;
    private PdfRenderer renderer;
    private ParcelFileDescriptor descriptor;
    private ZoomView viewer;
    private TextView title, position;
    private Button previous, next;
    private boolean chinese;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        chinese = !"en".equals(getIntent().getStringExtra("language"));
        try { tickets = new JSONArray(getIntent().getStringExtra("tickets")); } catch (Exception e) { finish(); return; }
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(16,16,16,16); root.setBackgroundColor(Color.rgb(255,250,242));
        root.setOnApplyWindowInsetsListener((view, insets) -> { view.setPadding(16 + insets.getSystemWindowInsetLeft(), 16 + insets.getSystemWindowInsetTop(), 16 + insets.getSystemWindowInsetRight(), 16 + insets.getSystemWindowInsetBottom()); return insets; });
        Button close = new Button(this); close.setText(chinese ? "返回行程" : "Back to itinerary"); close.setOnClickListener(v -> finish()); root.addView(close);
        title = new TextView(this); title.setTextSize(18); root.addView(title);
        position = new TextView(this); root.addView(position);
        LinearLayout controls = new LinearLayout(this);
        previous = new Button(this); previous.setText("‹"); previous.setOnClickListener(v -> step(-1));
        next = new Button(this); next.setText("›"); next.setOnClickListener(v -> step(1));
        Button minus = new Button(this); minus.setText("−"); minus.setOnClickListener(v -> viewer.adjust(.8f));
        Button plus = new Button(this); plus.setText("+"); plus.setOnClickListener(v -> viewer.adjust(1.25f));
        for (Button b : new Button[]{previous,next,minus,plus}) controls.addView(b,new LinearLayout.LayoutParams(0,LinearLayout.LayoutParams.WRAP_CONTENT,1));
        root.addView(controls); viewer = new ZoomView(); root.addView(viewer,new LinearLayout.LayoutParams(-1,0,1)); setContentView(root); loadDocument();
    }
    private void closePdf() { if (renderer != null) { renderer.close(); renderer=null; } if(descriptor != null) { try {descriptor.close();}catch(Exception ignored){} descriptor=null; } }
    private void loadDocument() {
        closePdf(); page=0; count=1;
        try {
            JSONObject ticket=tickets.getJSONObject(document); String path=ticket.getString("file");
            if (!path.matches("tickets/[A-Za-z0-9_.-]+\\.(pdf|png|jpg|jpeg)")) throw new Exception("Invalid path");
            title.setText(ticket.optString("title") + "\n" + ticket.optString("travelers"));
            if (path.endsWith(".pdf")) {
                File cached=new File(getCacheDir(),"ticket-view-"+document+".pdf");
                try(InputStream in=getAssets().open("www/"+path);FileOutputStream out=new FileOutputStream(cached)){byte[] b=new byte[8192];int n;while((n=in.read(b))>=0)out.write(b,0,n);}
                descriptor=ParcelFileDescriptor.open(cached,ParcelFileDescriptor.MODE_READ_ONLY); renderer=new PdfRenderer(descriptor); count=renderer.getPageCount(); renderPage();
            } else {
                BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;
                try(InputStream in=getAssets().open("www/"+path)){BitmapFactory.decodeStream(in,null,bounds);}
                BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=Math.max(1,Math.max(bounds.outWidth,bounds.outHeight)/2400);
                try(InputStream in=getAssets().open("www/"+path)){Bitmap bitmap=BitmapFactory.decodeStream(in,null,options);if(bitmap==null)throw new Exception("Image decode");viewer.setBitmap(bitmap);} updatePosition();
            }
        } catch(Exception e) { viewer.setBitmap(null); position.setText(chinese?"无法打开票据：文件损坏、加密或不支持。请返回并替换。":"Cannot open ticket: corrupt, encrypted, or unsupported. Return and replace it."); previous.setEnabled(document>0);next.setEnabled(document<tickets.length()-1); }
    }
    private void renderPage() {
        try(PdfRenderer.Page p=renderer.openPage(page)) {
            float scale=Math.min(3f,2400f/Math.max(p.getWidth(),p.getHeight())); Bitmap bitmap=Bitmap.createBitmap((int)(p.getWidth()*scale),(int)(p.getHeight()*scale),Bitmap.Config.ARGB_8888);bitmap.eraseColor(Color.WHITE);p.render(bitmap,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);viewer.setBitmap(bitmap);updatePosition();
        }catch(Exception e){position.setText(chinese?"页面无法显示":"Page could not be displayed");}
    }
    private void updatePosition(){position.setText((chinese?"文件 ":"Document ")+(document+1)+"/"+tickets.length()+" · "+(chinese?"页 ":"Page ")+(page+1)+"/"+count);previous.setEnabled(document>0||page>0);next.setEnabled(document<tickets.length()-1||page<count-1);}
    private void step(int direction){if(direction>0){if(page<count-1){page++;renderPage();}else if(document<tickets.length()-1){document++;loadDocument();}}else{if(page>0){page--;renderPage();}else if(document>0){document--;loadDocument();}}}
    @Override protected void onDestroy(){closePdf();if(viewer!=null)viewer.setBitmap(null);super.onDestroy();}
    private class ZoomView extends View {
        private Bitmap bitmap; private final Matrix matrix=new Matrix(); private float fit=1, zoom=1, tx=0, ty=0, lastX,lastY,startX,startY;private boolean scaled;
        private final ScaleGestureDetector detector;
        ZoomView(){super(TicketViewerActivity.this);setBackgroundColor(Color.rgb(228,224,214));detector=new ScaleGestureDetector(TicketViewerActivity.this,new ScaleGestureDetector.SimpleOnScaleGestureListener(){@Override public boolean onScale(ScaleGestureDetector d){scaled=true;adjust(d.getScaleFactor());return true;}});}
        void setBitmap(Bitmap value){Bitmap old=bitmap;bitmap=value;if(old!=null&&old!=value)old.recycle();reset();}
        void reset(){zoom=1;tx=0;ty=0;if(bitmap!=null&&getWidth()>0)fit=Math.min((float)getWidth()/bitmap.getWidth(),(float)getHeight()/bitmap.getHeight());invalidate();}
        void adjust(float factor){zoom=Math.max(1f,Math.min(8f,zoom*factor));invalidate();}
        @Override protected void onSizeChanged(int w,int h,int ow,int oh){reset();}
        @Override protected void onDraw(Canvas canvas){super.onDraw(canvas);if(bitmap==null)return;float scale=fit*zoom;matrix.reset();matrix.postScale(scale,scale);matrix.postTranslate((getWidth()-bitmap.getWidth()*scale)/2+tx,(getHeight()-bitmap.getHeight()*scale)/2+ty);canvas.drawBitmap(bitmap,matrix,null);}
        @Override public boolean onTouchEvent(MotionEvent e){detector.onTouchEvent(e);float x=e.getX(),y=e.getY();if(e.getActionMasked()==MotionEvent.ACTION_DOWN){lastX=startX=x;lastY=startY=y;scaled=false;}else if(e.getActionMasked()==MotionEvent.ACTION_MOVE&&e.getPointerCount()==1&&zoom>1){tx+=x-lastX;ty+=y-lastY;invalidate();}else if(e.getActionMasked()==MotionEvent.ACTION_UP){if(!scaled&&zoom==1&&Math.abs(x-startX)>100&&Math.abs(y-startY)<80)step(x<startX?1:-1);performClick();}lastX=x;lastY=y;return true;}
        @Override public boolean performClick(){super.performClick();return true;}
    }
}
