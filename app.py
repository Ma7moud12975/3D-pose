import streamlit as st
import requests
import json
import plotly.graph_objects as go
import numpy as np
import tempfile
import os
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="3D Pose Estimation",
    page_icon="🧍",
    layout="wide"
)

# Define API endpoint
API_URL = os.environ.get("API_URL", "http://localhost:8000")

def main():
    st.title("2D to 3D Pose Estimation")
    
    # Sidebar for options
    st.sidebar.title("Options")
    visualization_type = st.sidebar.radio(
        "Visualization Type",
        ["Static 3D", "Animation"]
    )
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "avi", "mov"])
    
    if uploaded_file is not None:
        # Save the file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}")
        temp_file.write(uploaded_file.read())
        temp_file.close()
        
        st.video(temp_file.name)
        
        # Process button
        if st.button("Convert to 3D"):
            with st.spinner("Processing video..."):
                # Call the API
                files = {"file": (uploaded_file.name, open(temp_file.name, "rb"), "video/mp4")}
                try:
                    response = requests.post(f"{API_URL}/api/process-video", files=files)
                    response.raise_for_status()
                    result = response.json()
                    
                    # Store the job ID in session state
                    st.session_state.job_id = result["job_id"]
                    st.session_state.result_url = result["result_url"]
                    
                    st.success("Video processed successfully!")
                    
                    # Fetch the results
                    fetch_and_display_results(result["result_url"], visualization_type)
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error processing video: {str(e)}")
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)
        
        # If we have a job ID in session state, show the results
        if "job_id" in st.session_state:
            if st.button("Show Results"):
                fetch_and_display_results(st.session_state.result_url, visualization_type)

def fetch_and_display_results(result_url, visualization_type):
    """Fetch results from API and display them"""
    try:
        response = requests.get(f"{API_URL}{result_url}")
        response.raise_for_status()
        pose_data = response.json()
        
        # Display the 3D visualization
        st.subheader("3D Pose Visualization")
        
        if visualization_type == "Static 3D":
            # Display a static 3D visualization of the first frame
            fig = visualize_3d_pose_static(pose_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Display an animated 3D visualization
            fig = visualize_3d_pose_animated(pose_data)
            st.plotly_chart(fig, use_container_width=True)
        
        # Provide download options
        st.subheader("Download Options")
        
        # Convert pose data to JSON string for download
        json_str = json.dumps(pose_data)
        st.download_button(
            label="Download 3D Pose Data (JSON)",
            data=json_str,
            file_name="pose_data.json",
            mime="application/json"
        )
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching results: {str(e)}")

def visualize_3d_pose_static(pose_data):
    """Create a static 3D visualization of pose data (first frame)"""
    # Get the first frame
    frame_data = pose_data["data"][0]
    
    # Extract x, y, z coordinates
    x = [point[0] for point in frame_data]
    y = [point[1] for point in frame_data]
    z = [point[2] for point in frame_data]
    
    # Create the 3D scatter plot
    fig = go.Figure(data=[go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=6,
            color=list(range(len(frame_data))),
            colorscale='Viridis',
            opacity=0.8
        )
    )])
    
    # Add connections between joints (simplified skeleton)
    # This is a simplified skeleton - you would need to adjust based on your keypoint format
    connections = [
        (0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6),  # Arms
        (0, 7), (7, 8), (8, 9), (0, 10), (10, 11), (11, 12),  # Legs
        (0, 13), (13, 14), (14, 15), (15, 16)  # Head and torso
    ]
    
    for connection in connections:
        if connection[0] < len(frame_data) and connection[1] < len(frame_data):
            fig.add_trace(go.Scatter3d(
                x=[frame_data[connection[0]][0], frame_data[connection[1]][0]],
                y=[frame_data[connection[0]][1], frame_data[connection[1]][1]],
                z=[frame_data[connection[0]][2], frame_data[connection[1]][2]],
                mode='lines',
                line=dict(color='black', width=4),
                showlegend=False
            ))
    
    # Update layout
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X'),
            yaxis=dict(title='Y'),
            zaxis=dict(title='Z'),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        scene_camera=dict(
            up=dict(x=0, y=1, z=0),
            center=dict(x=0, y=0, z=0),
            eye=dict(x=1.5, y=1.5, z=1.5)
        )
    )
    
    return fig

def visualize_3d_pose_animated(pose_data):
    """Create an animated 3D visualization of pose data"""
    frames_data = pose_data["data"]
    num_frames = min(len(frames_data), 100)  # Limit to 100 frames for performance
    
    # Create a figure with initial data (first frame)
    frame_data = frames_data[0]
    x = [point[0] for point in frame_data]
    y = [point[1] for point in frame_data]
    z = [point[2] for point in frame_data]
    
    fig = go.Figure(data=[go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=6,
            color=list(range(len(frame_data))),
            colorscale='Viridis',
            opacity=0.8
        ),
        name='joints'
    )])
    
    # Define connections (simplified skeleton)
    connections = [
        (0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6),  # Arms
        (0, 7), (7, 8), (8, 9), (0, 10), (10, 11), (11, 12),  # Legs
        (0, 13), (13, 14), (14, 15), (15, 16)  # Head and torso
    ]
    
    # Add initial connections
    for i, connection in enumerate(connections):
        if connection[0] < len(frame_data) and connection[1] < len(frame_data):
            fig.add_trace(go.Scatter3d(
                x=[frame_data[connection[0]][0], frame_data[connection[1]][0]],
                y=[frame_data[connection[0]][1], frame_data[connection[1]][1]],
                z=[frame_data[connection[0]][2], frame_data[connection[1]][2]],
                mode='lines',
                line=dict(color='black', width=4),
                name=f'connection_{i}',
                showlegend=False
            ))
    
    # Create frames for animation
    frames = []
    for i in range(num_frames):
        frame_data = frames_data[i]
        frame = {"data": [], "name": f"frame_{i}"}
        
        # Add markers for joints
        x = [point[0] for point in frame_data]
        y = [point[1] for point in frame_data]
        z = [point[2] for point in frame_data]
        
        frame["data"].append(go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='markers',
            marker=dict(
                size=6,
                color=list(range(len(frame_data))),
                colorscale='Viridis',
                opacity=0.8
            )
        ))
        
        # Add connections
        for connection in connections:
            if connection[0] < len(frame_data) and connection[1] < len(frame_data):
                frame["data"].append(go.Scatter3d(
                    x=[frame_data[connection[0]][0], frame_data[connection[1]][0]],
                    y=[frame_data[connection[0]][1], frame_data[connection[1]][1]],
                    z=[frame_data[connection[0]][2], frame_data[connection[1]][2]],
                    mode='lines',
                    line=dict(color='black', width=4)
                ))
        
        frames.append(frame)
    
    fig.frames = frames
    
    # Add animation controls
    fig.update_layout(
        updatemenus=[{
            "buttons": [
                {
                    "args": [None, {"frame": {"duration": 100, "redraw": True}, "fromcurrent": True}],
                    "label": "Play",
                    "method": "animate"
                },
                {
                    "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}],
                    "label": "Pause",
                    "method": "animate"
                }
            ],
            "direction": "left",
            "pad": {"r": 10, "t": 87},
            "showactive": False,
            "type": "buttons",
            "x": 0.1,
            "xanchor": "right",
            "y": 0,
            "yanchor": "top"
        }],
        sliders=[{
            "active": 0,
            "yanchor": "top",
            "xanchor": "left",
            "currentvalue": {
                "font": {"size": 16},
                "prefix": "Frame: ",
                "visible": True,
                "xanchor": "right"
            },
            "transition": {"duration": 300, "easing": "cubic-in-out"},
            "pad": {"b": 10, "t": 50},
            "len": 0.9,
            "x": 0.1,
            "y": 0,
            "steps": [
                {
                    "args": [
                        [f"frame_{i}"],
                        {"frame": {"duration": 100, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}
                    ],
                    "label": str(i),
                    "method": "animate"
                }
                for i in range(num_frames)
            ]
        }],
        scene=dict(
            xaxis=dict(title='X'),
            yaxis=dict(title='Y'),
            zaxis=dict(title='Z'),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        scene_camera=dict(
            up=dict(x=0, y=1, z=0),
            center=dict(x=0, y=0, z=0),
            eye=dict(x=1.5, y=1.5, z=1.5)
        )
    )
    
    return fig

if __name__ == "__main__":
    main()