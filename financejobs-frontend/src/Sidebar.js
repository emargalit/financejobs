import React from 'react';
import { Filter, MapPin } from 'lucide-react';

function Sidebar({
  selectedJobType,
  setSelectedJobType,
  selectedLocation,
  setSelectedLocation,
  allLocations
}) {
  const jobTypes = [
    "Festanstellung",
    "Praktika / Traineestellen",
    "Befristete Anstellung",
  ];

  return (
    <div className="sticky top-4 bg-white shadow-md rounded-2xl p-6 space-y-6 border border-gray-100">
      <div>
        <h3 className="text-lg font-semibold flex items-center mb-3">
          <Filter className="w-4 h-4 mr-2 text-gray-500" />
          Job Type
        </h3>
        <div className="space-y-2">
          {jobTypes.map(type => (
            <button
              key={type}
              onClick={() => setSelectedJobType(type)}
              className={`block w-full text-left px-3 py-2 text-sm rounded-xl border ${
                selectedJobType === type
                  ? "bg-blue-100 border-blue-400 font-semibold text-blue-800"
                  : "hover:bg-gray-50 border-gray-200"
              }`}
            >
              {type}
            </button>
          ))}
          {selectedJobType && (
            <button
              onClick={() => setSelectedJobType("")}
              className="text-sm text-red-500 mt-2 hover:underline"
            >
              Clear Job Type
            </button>
          )}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold flex items-center mb-3">
          <MapPin className="w-4 h-4 mr-2 text-gray-500" />
          Location
        </h3>
        <div className="space-y-2 max-h-[250px] overflow-y-auto">
          {allLocations.map(location => (
            <button
              key={location}
              onClick={() => setSelectedLocation(location)}
              className={`block w-full text-left px-3 py-2 text-sm rounded-xl border ${
                selectedLocation === location
                  ? "bg-blue-100 border-blue-400 font-semibold text-blue-800"
                  : "hover:bg-gray-50 border-gray-200"
              }`}
            >
              {location}
            </button>
          ))}
          {selectedLocation && (
            <button
              onClick={() => setSelectedLocation("")}
              className="text-sm text-red-500 mt-2 hover:underline"
            >
              Clear Location
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
