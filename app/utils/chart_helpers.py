# app/utils/chart_helpers.py

import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from plotly.subplots import make_subplots
import colorsys

logger = logging.getLogger(__name__)

class ChartHelpers:
    def __init__(self):
        """Initialize chart helpers"""
        # Color schemes
        self.color_schemes = {
            'primary': {
                'main': '#3498db',
                'light': '#5dade2',
                'dark': '#2980b9',
                'gradient': ['#3498db', '#2980b9']
            },
            'success': {
                'main': '#2ecc71',
                'light': '#58d68d',
                'dark': '#27ae60',
                'gradient': ['#2ecc71', '#27ae60']
            },
            'warning': {
                'main': '#f1c40f',
                'light': '#f4d03f',
                'dark': '#f39c12',
                'gradient': ['#f1c40f', '#f39c12']
            },
            'danger': {
                'main': '#e74c3c',
                'light': '#ec7063',
                'dark': '#c0392b',
                'gradient': ['#e74c3c', '#c0392b']
            }
        }
        
        # Chart templates
        self.templates = {
            'default': {
                'layout': {
                    'font_family': 'Arial, sans-serif',
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white',
                    'margin': dict(t=40, r=20, b=40, l=20),
                    'showlegend': True
                },
                'axes': {
                    'showgrid': True,
                    'gridcolor': '#f0f0f0',
                    'linecolor': '#e0e0e0'
                }
            },
            'dark': {
                'layout': {
                    'font_family': 'Arial, sans-serif',
                    'plot_bgcolor': '#1a1a1a',
                    'paper_bgcolor': '#1a1a1a',
                    'font_color': '#ffffff',
                    'margin': dict(t=40, r=20, b=40, l=20),
                    'showlegend': True
                },
                'axes': {
                    'showgrid': True,
                    'gridcolor': '#2d2d2d',
                    'linecolor': '#3d3d3d'
                }
            }
        }

    def create_line_chart(self,
                         data: pd.DataFrame,
                         x_column: str,
                         y_columns: Union[str, List[str]],
                         title: str = "",
                         template: str = "default",
                         color_scheme: str = "primary",
                         show_points: bool = True,
                         annotations: Optional[List[Dict]] = None) -> go.Figure:
        """Create a line chart"""
        try:
            fig = go.Figure()
            
            # Convert y_columns to list if string
            if isinstance(y_columns, str):
                y_columns = [y_columns]
            
            # Add traces for each y column
            for i, y_col in enumerate(y_columns):
                color = self._get_color_from_scheme(color_scheme, i, len(y_columns))
                
                fig.add_trace(go.Scatter(
                    x=data[x_column],
                    y=data[y_col],
                    name=y_col,
                    line=dict(color=color, width=2),
                    mode='lines+markers' if show_points else 'lines'
                ))
            
            # Apply template
            self._apply_template(fig, template)
            
            # Add title
            if title:
                fig.update_layout(title=title)
            
            # Add annotations if provided
            if annotations:
                fig.update_layout(annotations=annotations)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating line chart: {str(e)}")
            raise

    def create_bar_chart(self,
                        data: pd.DataFrame,
                        x_column: str,
                        y_column: str,
                        title: str = "",
                        template: str = "default",
                        color_scheme: str = "primary",
                        orientation: str = "v",
                        show_values: bool = True) -> go.Figure:
        """Create a bar chart"""
        try:
            color = self.color_schemes[color_scheme]['main']
            
            fig = go.Figure(data=[
                go.Bar(
                    x=data[x_column] if orientation == "v" else data[y_column],
                    y=data[y_column] if orientation == "v" else data[x_column],
                    orientation=orientation,
                    marker_color=color,
                    text=data[y_column] if show_values else None,
                    textposition='auto'
                )
            ])
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating bar chart: {str(e)}")
            raise

    def create_pie_chart(self,
                        data: pd.DataFrame,
                        values_column: str,
                        names_column: str,
                        title: str = "",
                        template: str = "default",
                        color_scheme: str = "primary",
                        hole: float = 0) -> go.Figure:
        """Create a pie/donut chart"""
        try:
            colors = self._generate_color_palette(
                len(data),
                base_color=self.color_schemes[color_scheme]['main']
            )
            
            fig = go.Figure(data=[
                go.Pie(
                    values=data[values_column],
                    labels=data[names_column],
                    hole=hole,
                    marker_colors=colors
                )
            ])
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating pie chart: {str(e)}")
            raise

    def create_scatter_plot(self,
                          data: pd.DataFrame,
                          x_column: str,
                          y_column: str,
                          size_column: Optional[str] = None,
                          color_column: Optional[str] = None,
                          title: str = "",
                          template: str = "default",
                          color_scheme: str = "primary") -> go.Figure:
        """Create a scatter plot"""
        try:
            fig = px.scatter(
                data,
                x=x_column,
                y=y_column,
                size=size_column,
                color=color_column,
                color_discrete_sequence=[self.color_schemes[color_scheme]['main']]
            )
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating scatter plot: {str(e)}")
            raise

    def create_heatmap(self,
                      data: pd.DataFrame,
                      title: str = "",
                      template: str = "default",
                      color_scheme: str = "primary",
                      show_values: bool = True) -> go.Figure:
        """Create a heatmap"""
        try:
            fig = go.Figure(data=go.Heatmap(
                z=data.values,
                x=data.columns,
                y=data.index,
                colorscale=self.color_schemes[color_scheme]['gradient'],
                text=data.values if show_values else None,
                texttemplate="%{text}" if show_values else None,
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating heatmap: {str(e)}")
            raise

    def create_radar_chart(self,
                          categories: List[str],
                          values: List[float],
                          title: str = "",
                          template: str = "default",
                          color_scheme: str = "primary") -> go.Figure:
        """Create a radar chart"""
        try:
            fig = go.Figure(data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                line_color=self.color_schemes[color_scheme]['main']
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(values)]
                    )
                ),
                showlegend=False
            )
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating radar chart: {str(e)}")
            raise

    def create_funnel_chart(self,
                          stages: List[str],
                          values: List[float],
                          title: str = "",
                          template: str = "default",
                          color_scheme: str = "primary") -> go.Figure:
        """Create a funnel chart"""
        try:
            fig = go.Figure(data=[
                go.Funnel(
                    y=stages,
                    x=values,
                    textinfo="value+percent initial",
                    marker=dict(
                        color=[self._get_color_from_scheme(
                            color_scheme, i, len(stages)
                        ) for i in range(len(stages))]
                    )
                )
            ])
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating funnel chart: {str(e)}")
            raise

    def create_gauge_chart(self,
                          value: float,
                          min_value: float = 0,
                          max_value: float = 100,
                          title: str = "",
                          template: str = "default",
                          color_scheme: str = "primary") -> go.Figure:
        """Create a gauge chart"""
        try:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [min_value, max_value]},
                    'bar': {'color': self.color_schemes[color_scheme]['main']},
                    'steps': [
                        {'range': [min_value, max_value], 
                         'color': self.color_schemes[color_scheme]['light']}
                    ]
                }
            ))
            
            self._apply_template(fig, template)
            
            if title:
                fig.update_layout(title=title)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating gauge chart: {str(e)}")
            raise

    def _apply_template(self, fig: go.Figure, template_name: str):
        """Apply template to figure"""
        template = self.templates.get(template_name, self.templates['default'])
        
        fig.update_layout(**template['layout'])
        fig.update_xaxes(**template['axes'])
        fig.update_yaxes(**template['axes'])

    def _get_color_from_scheme(self, 
                             scheme: str, 
                             index: int, 
                             total: int) -> str:
        """Get color from scheme based on index"""
        base_color = self.color_schemes[scheme]['main']
        if total == 1:
            return base_color
            
        hue, sat, val = colorsys.rgb_to_hsv(*self._hex_to_rgb(base_color))
        new_hue = (hue + (index / total)) % 1.0
        rgb = colorsys.hsv_to_rgb(new_hue, sat, val)
        return self._rgb_to_hex(rgb)

    def _generate_color_palette(self, 
                              n_colors: int, 
                              base_color: str) -> List[str]:
        """Generate color palette based on base color"""
        palette = []
        hue, sat, val = colorsys.rgb_to_hsv(*self._hex_to_rgb(base_color))
        
        for i in range(n_colors):
            new_hue = (hue + (i / n_colors)) % 1.0
            rgb = colorsys.hsv_to_rgb(new_hue, sat, val)
            palette.append(self._rgb_to_hex(rgb))
            
        return palette

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb: tuple) -> str:
        """Convert RGB color to hex"""
        return '#{:02x}{:02x}{:02x}'.format(
            int(rgb[0] * 255),
            int(rgb[1] * 255),
            int(rgb[2] * 255)
        )

# Initialize chart helpers
chart_helpers = ChartHelpers()

if __name__ == "__main__":
    # Test chart generation
    test_data = pd.DataFrame({
        'date': pd.date_range(start='2023-01-01', periods=10),
        'value1': np.random.randn(10).cumsum(),
        'value2': np.random.randn(10).cumsum(),
        'category': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    })
    
    # Test line chart
    line_chart = chart_helpers.create_line_chart(
        test_data,
        'date',
        ['value1', 'value2'],
        'Test Line Chart'
    )
    
    # Test bar chart
    bar_chart = chart_helpers.create_bar_chart(
        test_data,
        'category',
        'value1',
        'Test Bar Chart'
    )
    
    # Test pie chart
    pie_chart = chart_helpers.create_pie_chart(
        test_data,
        'value1',
        'category',
        'Test Pie Chart'
    )
    
    # Display charts (if running in Streamlit)
    import streamlit as st
    st.plotly_chart(line_chart)
    st.plotly_chart(bar_chart)
    st.plotly_chart(pie_chart)