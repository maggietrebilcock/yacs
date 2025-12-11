import React from "react";

export default function ProfilePage() {
  const user = {
    name: "Maggie Trebilcock",
    email: "trebim2@rpi.edu",
    cohort: "2023",
    majors: ["Computer Science"],
    minors: "N/A",
    pathway: "Philosophy & Logic",
    semesters: ["SPRING 2025"],
    degreePlans: ["Plan A", "Plan B"],
  };

  return (
    <div className="flex-grow p-6 bg-slate-50 text-slate-900 min-h-screen">
      <div className="max-w-6xl mx-auto grid grid-cols-12 gap-8 items-start">
        {/* LEFT COLUMN: avatar, edit button, friends column */}
        <aside className="col-span-4 flex flex-col items-center">
          <div className="w-40 h-40 rounded-full bg-gray-200 mb-4 shadow-inner" />
          <button className="px-4 py-2 rounded-md bg-white text-slate-900 font-medium border border-gray-200 mb-6 shadow-sm">
            Edit Profile
          </button>

          <div className="w-full mt-6">
            <div className="flex items-center gap-3">
              <div className="flex-1 border-t border-gray-300" />
              <span className="uppercase text-sm tracking-wider text-gray-500 w-24 text-left">
                my friends
              </span>
            </div>
            <div className="ml-6 mt-4 h-48 border-l border-gray-300" />
          </div>
        </aside>

        {/* RIGHT COLUMN: user info, majors, semesters, degree plans */}
        <main className="col-span-8">
          <h1 className="text-4xl font-semibold mb-2">{user.name}</h1>
          <div className="text-sm text-gray-600 mb-4">
            <div>{user.email}</div>
            <div className="mt-2">
              Cohort: <span className="font-medium text-gray-800">{user.cohort}</span>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-md p-4 mb-6 max-w-xl shadow-sm">
            <h3 className="text-sm text-gray-700 font-semibold mb-2">Major(s):</h3>
            <div className="text-base text-gray-800">{user.majors.join(", ")}</div>
            <div className="text-xs text-gray-500 mt-1">Systems and Software</div>
          </div>

          <div className="text-sm mb-6 max-w-xl text-gray-700">
            <div>
              Minor(s): <span className="font-medium text-gray-800">{user.minors}</span>
            </div>
            <div className="mt-2">
              HASS Pathway: <span className="font-medium text-gray-800">{user.pathway}</span>
            </div>
          </div>

          <section className="mb-6 max-w-2xl">
            <h4 className="text-sm uppercase tracking-wider text-gray-700 font-medium mb-2">My Semesters:</h4>
            <div className="text-xs text-gray-500 mb-3">{user.semesters[0]}</div>
            <div className="flex items-center gap-3">
              <div className="w-28 h-12 bg-white rounded-md border border-gray-200 shadow-sm" />
              <div className="w-28 h-12 bg-white rounded-md border border-gray-200 shadow-sm" />
              <div className="w-28 h-12 bg-white rounded-md border border-gray-200 shadow-sm" />
              <div className="w-10 h-12 bg-white rounded-md border border-gray-200 shadow-sm" />
            </div>
          </section>

          <section className="max-w-2xl">
            <h4 className="text-sm uppercase tracking-wider text-gray-700 font-medium mb-2">My Degree Plans:</h4>
            <div className="flex gap-4">
              <div className="w-36 h-12 bg-white rounded-md border border-gray-200 shadow-sm" />
              <div className="w-36 h-12 bg-white rounded-md border border-gray-200 shadow-sm" />
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}