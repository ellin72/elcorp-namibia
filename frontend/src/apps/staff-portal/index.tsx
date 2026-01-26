import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

const StaffPortal: React.FC = () => {
    return (
        <Routes>
            <Route path="/" element={<div className="container py-5"><h1>Staff Portal - Coming Soon</h1></div>} />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
};

export default StaffPortal;
