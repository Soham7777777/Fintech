from flask_wtf import FlaskForm # type: ignore
from wtforms import DateField, SelectField
from wtforms.validators import DataRequired
import datetime
from fintech import PatternTypes


class AllTimeHighForm(FlaskForm): # type: ignore
    date = DateField("Enter Date", validators=[DataRequired()], default=datetime.date.today())


class PatternsForm(FlaskForm): # type: ignore
    symbol = SelectField("Choose Symbol", validators=[DataRequired()], validate_choice=True)
    pattern = SelectField("Choose Pattern", validators=[DataRequired()], validate_choice=True, choices=[x.value for x in PatternTypes]) # type: ignore