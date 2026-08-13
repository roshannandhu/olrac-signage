package com.ablesign.bootlauncher;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.SystemClock;

public class BootReceiver extends BroadcastReceiver {
    private static final String ABLESIGN = "com.olrac.signage";

    @Override
    public void onReceive(final Context context, Intent intent) {
        Intent i = new Intent(Intent.ACTION_MAIN);
        i.setComponent(new ComponentName(ABLESIGN, ABLESIGN + ".MainActivity"));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);

        // AlarmManager fires via system — bypasses Realme/OPPO background launch restriction
        try {
            PendingIntent pi = PendingIntent.getActivity(context, 2, i,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
            AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            am.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, SystemClock.elapsedRealtime() + 6000, pi);
        } catch (Exception e) {
            // ignore
        }
    }
}
