import streamlit as st
import sympy as sp
import schemdraw
import schemdraw.elements as e
import io

# Define the Laplace variable
s = sp.symbols('s')

# Function to get lowest degree term in a polynomial
def lowest_degree_term(poly):
    terms = poly.as_dict()
    lowest_term = min(terms, key=lambda k: k[0])
    return terms[lowest_term], lowest_term[0]

# Function to get highest degree term in a polynomial
def lowest_degree_term_descending(poly):
    terms = poly.as_dict()
    highest_term = max(terms, key=lambda k: k[0])
    return terms[highest_term], highest_term[0]

# Function to add components to the drawing
def add_component_with_swap(d, component_type, value, parallel=False, last_component_end=None, swap_logic=False):
    if swap_logic:
        if component_type == 'L':
            component_type = 'C'
        elif component_type == 'C':
            component_type = 'L'
    return add_component(d, component_type, value, parallel, last_component_end)

def add_component(d, component_type, value, parallel=False, last_component_end=None):
    if parallel:
        d.push()
        if component_type == 'L':
            ind = d.add(e.Inductor().down())
            if last_component_end:
                ind.at(last_component_end)
            d.add(e.Label(f"{value} H", loc='center'))
        elif component_type == 'C':
            cap = d.add(e.Capacitor().down())
            if last_component_end:
                cap.at(last_component_end)
            d.add(e.Label(f"{value} F", loc='center'))
        elif component_type == 'R':
            res = d.add(e.Resistor().down())
            if last_component_end:
                res.at(last_component_end)
            d.add(e.Label(f"{value} Ω", loc='center'))
        d.pop()
    else:
        if component_type == 'L':
            ind = d.add(e.Inductor())
            d.add(e.Label(f"{value} H", loc='center'))
            return ind.center
        elif component_type == 'C':
            cap = d.add(e.Capacitor())
            d.add(e.Label(f"{value} F", loc='center'))
            return cap.center
        elif component_type == 'R':
            res = d.add(e.Resistor())
            d.add(e.Label(f"{value} Ω", loc='center'))
            return res.center

def generate_circuit_ascending(numerator, denominator, start_with_logic1=True):
    current_logic = start_with_logic1
    last_component_end = None
    
    with schemdraw.Drawing() as d:
        while not denominator.is_zero:
            num_coeff, num_deg = lowest_degree_term(numerator)
            den_coeff, den_deg = lowest_degree_term(denominator)
            quotient_term = (num_coeff / den_coeff) * s**(num_deg - den_deg)
            term_value = (1 / (num_coeff / den_coeff))

            # Check if the term is constant (i.e., degree of s is 0)
            if quotient_term.as_coeff_exponent(s)[1] == 0:
                component_type = 'R'  # Constants should be treated as Resistors
            else:
                component_type = 'L' if current_logic else 'C'

            is_parallel = not current_logic
            last_component_end = add_component_with_swap(d, component_type, term_value, parallel=is_parallel, last_component_end=last_component_end, swap_logic=True)

            new_numerator = (numerator.as_expr() - quotient_term * denominator.as_expr()).expand()
            numerator = sp.Poly(new_numerator, s)
            numerator, denominator = denominator, numerator
            current_logic = not current_logic
            
            if numerator.is_zero:
                break
        
        d.add(e.Ground())
        
        buffer = io.BytesIO()
        d.save(buffer)  # Removed format='png'
        buffer.seek(0)
        return buffer

def generate_circuit_descending(numerator, denominator, start_with_logic1=True):
    # Handle case where the degree of numerator is less than denominator, and swap if needed
    if numerator.degree() < denominator.degree():
        numerator, denominator = denominator, numerator
        start_with_logic1 = False  # Start with Y(s) when numerator is swapped
    
    current_logic = start_with_logic1
    last_component_end = None

    with schemdraw.Drawing() as d:
        while not denominator.is_zero:
            num_coeff, num_deg = lowest_degree_term_descending(numerator)
            den_coeff, den_deg = lowest_degree_term_descending(denominator)
            quotient_term = (num_coeff / den_coeff) * s**(num_deg - den_deg)
            term_value = num_coeff / den_coeff

            # Check if the term is constant (i.e., degree of s is 0)
            if quotient_term.as_coeff_exponent(s)[1] == 0:
                component_type = 'R'  # Constants should be treated as Resistors
            else:
                component_type = 'L' if current_logic else 'C'

            is_parallel = not current_logic
            last_component_end = add_component(d, component_type, term_value, parallel=is_parallel, last_component_end=last_component_end)

            new_numerator = (numerator.as_expr() - quotient_term * denominator.as_expr()).expand()
            numerator = sp.Poly(new_numerator, s)
            numerator, denominator = denominator, numerator
            current_logic = not current_logic

            if numerator.is_zero:
                break

        d.add(e.Ground())
        
        buffer = io.BytesIO()
        d.save(buffer)  # Removed format='png'
        buffer.seek(0)
        return buffer

def adjust_for_s_zero(numerator, denominator, start_with_logic1):
    # Check if numerator becomes 0 when s=0, and if so, swap the numerator and denominator
    if numerator.subs(s, 0) == 0:
        numerator, denominator = denominator, numerator
        start_with_logic1 = not start_with_logic1  # Swap starting logic as well
    return numerator, denominator, start_with_logic1

# Streamlit App
st.title("Circuit Synthesis Web Application")

# Input for numerator and denominator
numerator_input = st.text_input("Enter the numerator polynomial (e.g., 6*s**4 + 42*s**2 + 48):", "6*s**4 + 42*s**2 + 48")
denominator_input = st.text_input("Enter the denominator polynomial (e.g., s**5 + 18*s**3 + 48*s):", "s**5 + 18*s**3 + 48*s")

try:
    numerator = sp.Poly(sp.sympify(numerator_input), s)
    denominator = sp.Poly(sp.sympify(denominator_input), s)
except:
    st.error("Please enter valid polynomial expressions.")
    st.stop()

# Selection for Cauer type and start logic
choice = st.selectbox("Choose the Cauer type:", ["Cauer 1", "Cauer 2"])
start_with_logic1 = st.radio("Starting logic (select 'Z(s)' if Z(s) is given, else 'Y(s)'):", ['Z(s)', 'Y(s)']) == 'Z(s)'

# Adjust for the case where the numerator becomes zero when s=0
if choice == "Cauer 2":
    numerator, denominator, start_with_logic1 = adjust_for_s_zero(numerator, denominator, start_with_logic1)

# Generate Circuit based on user input
if st.button("Generate Circuit"):
    if choice == "Cauer 1":
        if numerator.degree() < denominator.degree():
            numerator, denominator = denominator, numerator
            start_with_logic1 = False  # Adjust starting logic for Cauer 1 when the numerator is swapped
        circuit_image = generate_circuit_descending(numerator, denominator, start_with_logic1=start_with_logic1)

    elif choice == "Cauer 2":
        circuit_image = generate_circuit_ascending(numerator, denominator, start_with_logic1=start_with_logic1)

    st.image(circuit_image, caption="Generated Circuit", use_column_width=True)
