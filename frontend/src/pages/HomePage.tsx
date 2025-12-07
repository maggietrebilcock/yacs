import React from "react";
import ScheduleList from "../components/ScheduleList";
import WeekScheduler from "../components/WeekScheduler";

export default function HomePage() {
  return (
    <main className="flex-1 p-4">
      <WeekScheduler events={[]} startHour={8} endHour={20} showWeekend={false} />
      <ScheduleList />
    </main>
  );
}
