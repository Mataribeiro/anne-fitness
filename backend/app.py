from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Product, Transaction
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Cadastro de produtos (GET exibe formulário, POST cadastra)
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastro_produtos():
    if request.method == 'POST':
        nome = request.form['nome']
        tamanho = request.form['tamanho']
        cor = request.form['cor']
        preco_compra = float(request.form['preco_compra'])
        preco_venda = float(request.form['preco_venda'])
        estoque = int(request.form['estoque'])

        produto = Product(
            nome=nome,
            tamanho=tamanho,
            cor=cor,
            preco_compra=preco_compra,
            preco_venda=preco_venda,
            estoque=estoque
        )
        db.session.add(produto)
        db.session.commit()
        return redirect(url_for('estoque_view'))
    return render_template('cadastro-de-produtos.html')

# Página de estoque
@app.route('/estoque')
def estoque_view():
    produtos = Product.query.all()
    total_compra = sum(p.preco_compra * p.estoque for p in produtos)
    total_venda = sum(p.preco_venda * p.estoque for p in produtos)
    total_lucro = total_venda - total_compra
    return render_template('estoque.html', produtos=produtos,
                           total_compra=total_compra,
                           total_venda=total_venda,
                           total_lucro=total_lucro)

# Adicionar estoque
@app.route('/adicionar/<int:id>', methods=['POST'])
def adicionar_estoque(id):
    produto = Product.query.get(id)
    if not produto:
        return jsonify({'mensagem': 'Produto não encontrado'}), 404
    quantidade = int(request.form['quantidade'])
    produto.estoque += quantidade
    transacao = Transaction(produto_id=id, tipo='compra', quantidade=quantidade)
    db.session.add(transacao)
    db.session.commit()
    return redirect(url_for('estoque_view'))

# Remover estoque (ajuste, não venda)
@app.route('/remover/<int:id>', methods=['POST'])
def remover_estoque(id):
    produto = Product.query.get(id)
    if not produto:
        return jsonify({'mensagem': 'Produto não encontrado'}), 404
    quantidade = int(request.form['quantidade'])
    if quantidade > produto.estoque:
        return jsonify({'mensagem': 'Quantidade maior que o estoque atual'}), 400
    produto.estoque -= quantidade
    transacao = Transaction(produto_id=id, tipo='ajuste', quantidade=quantidade)
    db.session.add(transacao)
    db.session.commit()
    return redirect(url_for('estoque_view'))

# Vender produto
@app.route('/vender/<int:id>', methods=['POST'])
def vender_produto(id):
    produto = Product.query.get(id)
    if not produto:
        return jsonify({'mensagem': 'Produto não encontrado'}), 404
    if produto.estoque <= 0:
        return jsonify({'mensagem': 'Estoque insuficiente'}), 400
    transacao = Transaction(produto_id=id, tipo='venda', quantidade=1)
    produto.estoque -= 1
    db.session.add(transacao)
    db.session.commit()
    return redirect(url_for('estoque_view'))

# Excluir produto
@app.route('/excluir/<int:id>', methods=['POST'])
def excluir_produto(id):
    produto = Product.query.get(id)
    if produto:
        db.session.delete(produto)
        db.session.commit()
    return redirect(url_for('estoque_view'))

# Página de vendas com filtros
@app.route('/vendas')
def vendas():
    product_id = request.args.get('product_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    vendas_query = Transaction.query.filter_by(tipo='venda')
    if product_id:
        vendas_query = vendas_query.filter_by(produto_id=product_id)
    if start_date:
        vendas_query = vendas_query.filter(Transaction.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        vendas_query = vendas_query.filter(Transaction.timestamp <= datetime.strptime(end_date, '%Y-%m-%d'))

    vendas = vendas_query.order_by(Transaction.timestamp.desc()).all()
    products = Product.query.order_by(Product.nome).all()

    for venda in vendas:
        venda.total_value = venda.quantidade * venda.product.preco_venda

    return render_template('vendas.html', vendas=vendas, products=products, request=request)

# Excluir venda
@app.route('/excluir_venda/<int:id>', methods=['POST'])
def excluir_venda(id):
    venda = Transaction.query.get(id)
    if not venda or venda.tipo != 'venda':
        return jsonify({'mensagem': 'Venda não encontrada'}), 404
    db.session.delete(venda)
    db.session.commit()
    return redirect(url_for('vendas'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)